# Deployment on Azure

CrossSellIQ runs on Azure Container Apps behind one public URL:

**https://crossselliq.salmonpond-b87be68e.germanywestcentral.azurecontainerapps.io/**

This document describes the deployment architecture, how a change reaches production, how the database in the cloud is updated, what it costs, and how to rebuild the Azure setup from scratch.

## Architecture

```
Local machine                         GitHub                               Azure (resource group rg-crossselliq, Germany West Central)
-------------                         ------                               ------------------------------------------------------------
data/raw/*.csv                        push or merge to main
      |                                     |
pipeline/run_pipeline.py                    v
      |                               GitHub Actions (ci.yml)
data/crossselliq.duckdb (3.1 GB)        1. build-and-test
      |                                 2. publish-image ----------> GitHub Container Registry
pipeline/export_gold.py                 3. deploy                      ghcr.io/r1057802/crossselliq-api:<commit SHA>
      |                                     |                                 |
data/crossselliq_gold.duckdb (~170 MB)      | OIDC login, no password         | image pull (public package)
      |                                     v                                 v
      |  az storage file upload        Managed identity  -- Contributor --> Container App "crossselliq"
      |                                id-crossselliq-github  on rg only    (API + web page, port 8080)
      v                                                                       |
Storage account stcrossselliq1057                                             | read-only mount at /data
  file share gold-data  <-----------------------------------------------------+
  crossselliq_gold.duckdb                                                     |
                                                                              v
                                                     https://crossselliq.salmonpond-b87be68e.germanywestcentral.azurecontainerapps.io/
```

| Component | Azure or GitHub resource | Role |
|---|---|---|
| Resource group | `rg-crossselliq` | Holds every Azure resource of the project, so costs are visible per project and everything can be removed at once |
| Region | `germanywestcentral` | Azure for Students only allows five regions; this is the closest one inside the EU that offers every service used |
| Container registry | GitHub Container Registry, package `crossselliq-api` | Stores the API image. Free, and GitHub Actions can push to it with the built-in `GITHUB_TOKEN` |
| Container Apps environment | `cae-crossselliq`, mode `WorkloadProfiles`, Consumption profile | Network and runtime for the container. Pay per use |
| Container App | `crossselliq` | Runs the API image. External HTTPS ingress on port 8080, scales between 0 and 1 replica |
| Storage account | `stcrossselliq1057`, `Standard_LRS`, TLS 1.2, no public blob access | Private storage for the database file |
| File share | `gold-data`, quota 1 GB | Holds `crossselliq_gold.duckdb`, mounted read-only in the container |
| Managed identity | `id-crossselliq-github` | The identity GitHub Actions uses to deploy. Role `Contributor` on `rg-crossselliq` only |
| Log Analytics workspace | created automatically with the environment | Container logs, for troubleshooting |

### Why the pipeline does not run in the cloud

The pipeline needs the 3.5 GB Kaggle transactions file and builds a 3.1 GB database. The API only reads four small Gold tables. Running the pipeline in the cloud would cost more, take longer, and put the raw Kaggle data in Azure. Instead, the pipeline runs locally and only the Gold tables are uploaded to private storage.

### The gold-only database

`pipeline/export_gold.py` copies the `gold` schema into `data/crossselliq_gold.duckdb`:

- It opens the full database read-only and does not change it.
- It checks that every table has the same number of rows as the source, and stops with an error otherwise.
- It writes to a temporary file and only replaces the old file when every check passed.
- It is rebuilt from scratch on every run. The file is small and fully derived from Gold, so a full rebuild is simpler than an incremental update and can never keep stale rows. The pipeline itself stays incremental.
- Primary key indexes are left out and rows are sorted by their key instead. The file is read-only, so the indexes add nothing there, and they tripled the size (787 MB with indexes, about 170 MB without). Sorting lets DuckDB skip most of the data when the API looks up one customer: a recommendation request took about 4.5 ms against 11.5 ms with the indexes in a local test.

The deployed image never contains data. The container reads the database from the file share, and `Database__Path` points the API to it.

## From push to production

`.github/workflows/ci.yml` runs on every push. Each job only starts when the previous one succeeded, so a broken version never reaches production.

| Job | Runs on | What it does |
|---|---|---|
| `build-and-test` | every branch | Restores, builds, and tests the .NET solution, then builds both Docker images |
| `publish-image` | `main`, or a manual run | Builds the API image and pushes it to GHCR with two tags: the commit SHA and `latest` |
| `deploy` | `main` only | Logs in to Azure with OIDC, sets the Container App to the image of this commit, and waits until `/health` returns `200` |

On a feature branch only `build-and-test` runs, so a pull request shows whether the change builds and passes the tests without changing production.

To see which commit is live:

```powershell
az containerapp show --name crossselliq --resource-group rg-crossselliq --query "properties.template.containers[0].image" --output tsv
```

The tag after `crossselliq-api:` is the commit SHA.

### Authentication without passwords

The `deploy` job logs in with OpenID Connect (OIDC). For every run, GitHub issues a short-lived token that states which repository and branch the workflow belongs to. Azure accepts it because the managed identity has a federated credential that trusts exactly that subject:

```
repo:r1057802@186014311/crosssell-iq@1400585094:ref:refs/heads/main
```

The numbers are the fixed IDs of the GitHub account and repository. A workflow from another repository or from a feature branch cannot log in.

GitHub stores three repository secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_SUBSCRIPTION_ID`. They identify the managed identity, the directory, and the subscription. None of them is a password, and no password exists anywhere in the setup.

The image is pushed with the built-in `GITHUB_TOKEN`, which GitHub creates per run. Only the `publish-image` job may write packages, and only the `deploy` job may request an OIDC token.

### Rolling back

Every deployed version is an image tagged with its commit SHA. To return to an earlier version, set the Container App to that tag:

```powershell
az containerapp update --name crossselliq --resource-group rg-crossselliq --image ghcr.io/r1057802/crossselliq-api:<earlier commit SHA>
```

The next merge to `main` deploys the newest commit again.

## Updating the database in the cloud

The cloud database only changes when it is uploaded again. Run these commands in PowerShell from the project root (the `$revision` variable does not work in the classic command prompt):

```powershell
.venv\Scripts\python.exe pipeline\run_pipeline.py
.venv\Scripts\python.exe pipeline\export_gold.py
az storage file upload --account-name stcrossselliq1057 --share-name gold-data --source data\crossselliq_gold.duckdb
$revision = az containerapp show --name crossselliq --resource-group rg-crossselliq --query properties.latestRevisionName --output tsv
az containerapp revision restart --name crossselliq --resource-group rg-crossselliq --revision $revision
```

The restart makes sure the running container opens the new file. The API opens a new read-only connection per request, so the database never needs to be locked for writing in the cloud.

The upload replaces the file on the share in place. If it stops before 100% (for example with a network timeout), the share holds an incomplete file and the live app can fail. Run the upload again until it reaches 100%, then restart the revision. Check the result with `/health`.

## Costs and cost control

The project runs on an **Azure for Students** subscription: a student credit without a credit card. When the credit runs out, the resources stop; nothing is charged.

| Resource | What drives the cost | Cost control |
|---|---|---|
| Container App | vCPU-seconds and GiB-seconds while a replica runs, plus requests | `minReplicas: 0`: no replica runs while nobody uses the app. Small size: 0.5 vCPU and 1 GiB. `maxReplicas: 1` caps the cost under load |
| Azure Files | stored data and transactions | One file of about 170 MB, share quota limited to 1 GB |
| Log Analytics | ingested log data | One small app with little traffic produces little log data |
| GitHub Container Registry | none | Free for public packages |
| GitHub Actions | none | Free for public repositories |

The Container Apps Consumption plan includes a monthly free grant per subscription. At the time of writing, the [Azure Container Apps pricing page](https://azure.microsoft.com/pricing/details/container-apps/) lists 180,000 vCPU-seconds, 360,000 GiB-seconds, and 2 million requests per month. With 0.5 vCPU and 1 GiB, one active hour uses 1,800 vCPU-seconds and 3,600 GiB-seconds, so the free grant covers about 100 active hours per month. Check the pricing page before relying on these numbers; they can change.

### Budget alert

A budget on the subscription sends an email when the actual costs reach a share of a monthly amount:

| Setting | Value |
|---|---|
| Name | `budget-crossselliq` |
| Scope | the Azure for Students subscription |
| Amount | 10 per month, in the billing currency of the subscription |
| Reset period | monthly |
| Alerts | actual costs at 50%, 80%, and 100% of the budget, sent by email |

How it works:

- Azure compares the actual costs of the subscription in the current month with the budget. When a threshold is crossed, it sends one email for that threshold. The budget starts again at zero every month.
- A budget only warns. It does not stop or delete any resource. The hard limit is the student credit: when it runs out, the resources stop and nothing is charged.
- Cost data in Azure arrives with a delay of several hours, so an alert is not instant. It is meant to catch a trend, such as an app that no longer scales to zero.
- The amount is far above the expected cost. Normal use stays within the free grant of Container Apps and costs a few cents for storage, so an alert means something changed and needs a look.

To check or change it: Azure Portal, Subscriptions, Azure for Students, Cost Management, Budgets.

### Cost analysis

Cost Management, Cost analysis, filtered on `rg-crossselliq`, shows the actual cost per resource and per day. Use it to explain where the money goes and to check that the app costs close to nothing while idle.

### Cold start

Because the app scales to zero, the first request after a quiet period starts a new replica. That request takes a few seconds longer. Open the URL shortly before a demo. To avoid cold starts during the exam, set the minimum to one replica temporarily and back to zero afterwards:

```powershell
az containerapp update --name crossselliq --resource-group rg-crossselliq --min-replicas 1
az containerapp update --name crossselliq --resource-group rg-crossselliq --min-replicas 0
```

A running replica uses the free grant continuously, so do not leave the minimum at one.

## Setting up Azure from scratch

These steps were run once to create the environment. Run them in PowerShell (not the classic command prompt, because some steps use PowerShell variables) with the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed.

### 1. Sign in and prepare the subscription

```powershell
az login
az account set --subscription "Azure for Students"
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.ManagedIdentity
az extension add --name containerapp --upgrade
```

A school account can also see a school subscription without rights to register services. Select the Azure for Students subscription explicitly.

Azure for Students only allows deployment in a few regions. Check which ones:

```powershell
az policy assignment list --query "[].{name:displayName, regions:parameters.listOfAllowedLocations.value}" --output json
```

### 2. Resource group and storage

```powershell
az group create --name rg-crossselliq --location germanywestcentral
az storage account create --name stcrossselliq1057 --resource-group rg-crossselliq --location germanywestcentral --sku Standard_LRS --kind StorageV2 --min-tls-version TLS1_2 --allow-blob-public-access false
az storage share-rm create --resource-group rg-crossselliq --storage-account stcrossselliq1057 --name gold-data --quota 1
.venv\Scripts\python.exe pipeline\export_gold.py
az storage file upload --account-name stcrossselliq1057 --share-name gold-data --source data\crossselliq_gold.duckdb
```

Storage account names are global: another name may be needed when rebuilding.

### 3. Container Apps environment with the file share

```powershell
az containerapp env create --name cae-crossselliq --resource-group rg-crossselliq --location germanywestcentral --environment-mode WorkloadProfiles
$key = az storage account keys list --account-name stcrossselliq1057 --resource-group rg-crossselliq --query "[0].value" --output tsv
az containerapp env storage set --name cae-crossselliq --resource-group rg-crossselliq --storage-name golddata --azure-file-account-name stcrossselliq1057 --azure-file-account-key $key --azure-file-share-name gold-data --access-mode ReadOnly
```

`--environment-mode WorkloadProfiles` is required. Without it, the current Azure CLI extension creates an Express environment, which does not support mounted storage. The mode of an environment cannot be changed afterwards.

The storage key is only kept in the `$key` variable and stays inside Azure afterwards. It is never stored in the repository.

### 4. Container App

The configuration is in `deploy/containerapp.template.yaml`. The placeholder `__ENVIRONMENT_ID__` is filled in just before deployment, so the subscription ID stays out of Git.

```powershell
$envId = az containerapp env show --name cae-crossselliq --resource-group rg-crossselliq --query id --output tsv
(Get-Content deploy\containerapp.template.yaml) -replace '__ENVIRONMENT_ID__', $envId | Set-Content "$env:TEMP\containerapp.yaml" -Encoding ascii
az containerapp create --name crossselliq --resource-group rg-crossselliq --yaml "$env:TEMP\containerapp.yaml"
az containerapp show --name crossselliq --resource-group rg-crossselliq --query properties.configuration.ingress.fqdn --output tsv
```

The template sets the image, HTTPS ingress on port 8080, the read-only share at `/data`, `Database__Path=/data/crossselliq_gold.duckdb`, 0.5 vCPU and 1 GiB, a readiness probe on `/health`, and scaling between 0 and 1 replica.

The image must be public on GHCR (GitHub profile, Packages, `crossselliq-api`, Package settings, Change visibility), so Azure can pull it without credentials. The image contains only the application, no data or secrets.

### 5. Identity for GitHub Actions

```powershell
az identity create --name id-crossselliq-github --resource-group rg-crossselliq --location germanywestcentral
$principalId = az identity show --name id-crossselliq-github --resource-group rg-crossselliq --query principalId --output tsv
$rgId = az group show --name rg-crossselliq --query id --output tsv
az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal --role Contributor --scope $rgId
az identity federated-credential create --name github-main --identity-name id-crossselliq-github --resource-group rg-crossselliq --issuer https://token.actions.githubusercontent.com --subject "repo:r1057802@186014311/crosssell-iq@1400585094:ref:refs/heads/main" --audiences api://AzureADTokenExchange
```

A user-assigned managed identity lives in the resource group, so it needs no rights to register applications in the school directory.

GitHub shows the exact subject it sends in the log of the `Log in to Azure with OIDC` step ("subject claim"). The federated credential must match it exactly.

Then add three repository secrets in GitHub (Settings, Secrets and variables, Actions):

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | `clientId` of the managed identity (`az identity show --name id-crossselliq-github --resource-group rg-crossselliq --query clientId --output tsv`) |
| `AZURE_TENANT_ID` | `az account show --query tenantId --output tsv` |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query id --output tsv` |

### Removing everything

```powershell
az group delete --name rg-crossselliq --yes
```

This deletes every Azure resource of the project, including the stored database. The GitHub package and secrets are removed separately on GitHub.

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `RequestDisallowedByAzure` when creating a resource | The region is not allowed for Azure for Students. List the allowed regions (step 1) and use one of them. |
| `AuthorizationFailed` on `az provider register` | The school subscription is selected. Run `az account set --subscription "Azure for Students"`. |
| `ExpressEnvironmentResourceNotSupported` when adding storage | The environment was created in Express mode. Delete it and create it again with `--environment-mode WorkloadProfiles`. |
| `AADSTS700213: No matching federated identity record found` in the `deploy` job | The federated credential subject does not match what GitHub sends. Copy the subject claim from the job log and update the credential with `az identity federated-credential update`. |
| `deploy` fails at the health check | The new version does not start or cannot read the database. Run `az containerapp logs show --name crossselliq --resource-group rg-crossselliq --tail 50` and roll back if needed. |
| `/health` returns `Unhealthy` in the cloud | The file is missing on the share or the name does not match `Database__Path`. Check with `az storage file list --account-name stcrossselliq1057 --share-name gold-data --output table`. |
| The first request is slow | Cold start after scaling to zero. See Cold start. |
