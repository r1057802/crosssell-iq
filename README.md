# CrossSellIQ

CrossSellIQ recommends product categories that an existing H&M customer has never bought before. It consists of a Python and DuckDB data pipeline, an ASP.NET Core API, and a web page served by that API.

This version is the **baseline** (Milestone 1): it recommends the most popular categories the customer has not bought yet, ranked by popularity. Every customer gets the same ranking, minus the categories they already bought. Personalized recommendations follow in a later milestone.

School project for Cloud & Ops and Artificial Intelligence, Thomas More (2026-2027).

## How it works

```
data/raw/*.csv  ->  pipeline (Python + DuckDB)  ->  data/crossselliq.duckdb  ->  API (C#)  ->  web page
                    bronze -> silver -> gold         gold tables only            read-only
```

- The **pipeline** runs separately and in advance. It loads the Kaggle CSV files into DuckDB and builds small Gold tables for the API.
- The **API** only reads the Gold tables, in read-only mode. It never runs the pipeline and never reads the full transactions.
- The **web page** is plain HTML, CSS, and JavaScript in `src/CrossSellIQ.Api/wwwroot`, served by the API.

## Requirements

| Tool | Version used | Needed for |
|---|---|---|
| Windows with PowerShell | Windows 11 | the commands below |
| Python | 3.14 | the data pipeline |
| .NET SDK | 10.0 | the API, web page, and tests |
| Kaggle account and Kaggle CLI | | downloading the data |
| Free disk space | about 7 GB | raw CSV files (3.7 GB) and the database (about 3 GB) |

The data and the database are not in Git. Every setup downloads the data and builds the database locally.

## 1. Get the code and set up Python

From the folder where you want the project:

```powershell
git clone https://github.com/r1057802/crosssell-iq.git
cd crosssell-iq
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

To run the notebooks in `notebooks/` as well, install the development packages:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## 2. Download the data

The data comes from the Kaggle competition [H&M Personalized Fashion Recommendations](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations). Only three files are used; the product images are not needed.

1. Sign in on Kaggle and accept the competition rules on the competition page (Data tab). Downloads fail until you do.
2. Install the Kaggle CLI and sign in:

   ```powershell
   .venv\Scripts\python.exe -m pip install kaggle
   .venv\Scripts\kaggle.exe auth login
   ```

3. Download the three files into `data/raw`:

   ```powershell
   foreach ($file in "articles.csv", "customers.csv", "transactions_train.csv") {
       .venv\Scripts\kaggle.exe competitions download -c h-and-m-personalized-fashion-recommendations -f $file -p data\raw
   }
   ```

4. If Kaggle saved `.zip` files, extract them and remove the archives:

   ```powershell
   Get-ChildItem data\raw\*.zip | ForEach-Object {
       Expand-Archive $_.FullName -DestinationPath data\raw -Force
       Remove-Item $_.FullName
   }
   ```

`data/raw` must now contain `articles.csv`, `customers.csv`, and `transactions_train.csv`. Never edit these files: they are the raw source of the pipeline.

## 3. Build the database

```powershell
.venv\Scripts\python.exe pipeline\run_pipeline.py
```

This runs Bronze, Silver, and Gold in order and creates `data/crossselliq.duckdb`. The first run loads 31.8 million transactions and can take several minutes. Every layer runs its quality checks and stops with an error if one fails. The last lines should be:

```
No Silver changes: Gold is already up to date.    (or: Gold refreshed in ... s)
All 10 Gold checks passed.
```

The pipeline is incremental: a second run processes nothing new and changes nothing.

| Command | Purpose |
|---|---|
| `.venv\Scripts\python.exe pipeline\check_quality.py` | Validate an existing database without changing it |
| `.venv\Scripts\python.exe pipeline\raw_to_bronze.py` | Run one layer (also `bronze_to_silver.py`, `silver_to_gold.py`) |
| `.venv\Scripts\python.exe pipeline\run_pipeline.py --full-refresh` | Rebuild everything from the raw files |

DuckDB allows only one writer at a time. Close notebook kernels that have the database open before running the pipeline. A running API does not block the pipeline: it opens a read-only connection per request and closes it right away.

## 4. Run the API and the web page

```powershell
dotnet run --project src/CrossSellIQ.Api --launch-profile http
```

Then open:

- Web page: http://localhost:5168/
- Health check: http://localhost:5168/health (shows `Healthy`)

On the web page, select one of the example customers, or paste a customer ID and select **Get recommendations**. Stop the API with `Ctrl+C`.

## 5. Run the tests

```powershell
dotnet test
```

The tests use an in-memory fake repository instead of the database, so they also run without the data (for example in CI). They check that:

- a valid customer gets recommendations;
- an unknown customer returns `404`, and invalid input returns `400`;
- categories the customer already bought are never recommended;
- recommendations are sorted by score;
- an unavailable database returns `503` without internal details.

## API

All responses are JSON. Errors use the standard [problem details](https://www.rfc-editor.org/rfc/rfc9457) format with a `title` and `detail`.

### `GET /api/recommendations/{customerId}`

Baseline recommendations for one customer.

| Parameter | Where | Rules |
|---|---|---|
| `customerId` | path | 64-character hexadecimal hash; surrounding spaces and uppercase letters are accepted |
| `limit` | query, optional | 1 to 20, default 5 |

Example: `GET /api/recommendations/0000423b00ade91418cceaf3b26c6af3dd342b51fd051eec9c12fb36984420fa?limit=2`

```json
{
  "customerId": "0000423b00ade91418cceaf3b26c6af3dd342b51fd051eec9c12fb36984420fa",
  "recommendations": [
    { "category": "Socks & Tights", "score": 0.2445, "reason": "Popular category this customer has not bought before" },
    { "category": "Nightwear", "score": 0.1553, "reason": "Popular category this customer has not bought before" }
  ],
  "purchasedCategories": ["Accessories", "Garment Full body", "Garment Lower body", "Garment Upper body", "Shoes", "Swimwear", "Underwear"],
  "message": null
}
```

| Situation | Status | Response |
|---|---|---|
| Customer found | `200` | Recommendations, highest score first |
| Customer has no purchases in a recommendable category | `200` | The most popular categories, with a `message` |
| Customer already bought every category | `200` | Empty `recommendations`, with a `message` |
| Customer ID is empty or not a 64-character hash, or `limit` is out of range | `400` | Problem details |
| Customer ID is valid but not in the dataset | `404` | Problem details |
| Database unavailable | `503` | Problem details; the cause is only written to the server log |

### `GET /api/example-customers`

Twelve real customers from `gold.example_customers` with different purchase histories (0, 1, 2 to 3, and 4 or more categories), used by the web page for demos.

```json
[
  { "customerId": "00058ecf091cea1bba9d800cabac6ed1ae284202cdab68bec5c8429eb3271c0c", "purchasedCategoryCount": 0 }
]
```

### `GET /health`

Returns `Healthy` (`200`) when the API runs and the Gold tables can be read, otherwise `Unhealthy` (`503`).

## The baseline score

`score` is `gold.category_popularity.popularity_score`: the number of distinct customers who bought the category, divided by the number of distinct buyers of the most popular category. It ranges from 0 to 1, where 1 is the most popular category (Garment Upper body).

The score measures popularity across all customers. It is **not** a predicted probability that this customer will buy the category.

Two data rules affect the result:

- The `Unknown` product group is never recommended and does not count as a purchased category. 506 customers only bought `Unknown` articles; like the 9,699 customers who never bought anything, they have no recommendable purchase history and get the most popular categories.
- Very small categories (for example `Fun`, with 5 buyers) stay recommendable, but their score is close to 0, so they always rank last.

## Configuration

The API reads the database path from `Database:Path` in `src/CrossSellIQ.Api/appsettings.json`. A relative path is resolved from the API project folder. The default is `../../data/crossselliq.duckdb`.

Override it with an environment variable, for example:

```powershell
$env:Database__Path = "D:\data\crossselliq.duckdb"
dotnet run --project src/CrossSellIQ.Api --launch-profile http
```

The API stops at startup when the path is empty. When the file is missing or locked, the API still starts, but `/health` and the recommendation endpoints return `503`.

This version has no secrets and needs no `.env` file.

## Project structure

```
crosssell-iq/
├── src/CrossSellIQ.Api/       # ASP.NET Core API: Controllers -> Services -> Repositories -> DuckDB; web page in wwwroot
├── tests/CrossSellIQ.Api.Tests/  # xUnit tests with a fake repository
├── pipeline/                  # raw -> bronze -> silver -> gold scripts and quality checks
├── notebooks/                 # the same pipeline built step by step, plus exploration
├── data/                      # raw CSV files and the DuckDB database (not in Git)
├── docs/                      # assignment and logbook
├── CrossSellIQ.slnx           # .NET solution: API and tests
├── requirements.txt           # Python packages for the pipeline
└── requirements-dev.txt       # extra packages for the notebooks
```

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `IO Error: Cannot open file "...crossselliq.duckdb"` (the file is used by another process) when running the pipeline | Another process has the database open, usually a notebook kernel or the DuckDB UI. Close it and run the pipeline again. |
| `/health` shows `Unhealthy` | The database does not exist yet (run step 3) or the path is wrong (see Configuration). The API console shows the cause. |
| `No raw file found for: [...]` | A CSV file is missing in `data/raw` (see step 2). |
| `kaggle` returns `403 Forbidden` | Accept the competition rules on the Kaggle website first. |
