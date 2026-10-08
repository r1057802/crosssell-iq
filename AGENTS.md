# Agent Project Context

## How to use this file

This file, `AGENTS.md`, is read by AI coding agents other than Claude Code (for example Codex). It has the same content as `CLAUDE.md`, which Claude Code reads. Agents must treat these instructions as the default rules for the entire project.

Keep both files identical apart from this section: when one changes, update the other in the same step.

## User context

- My name is Nicolas Diaz Valencia.
- I am a student in Applied Data Intelligence at Thomas More.
- I build projects for learning, my portfolio, school assignments, and future job applications.
- Explain important technical choices clearly so I can understand and defend the work myself.
- Prefer practical, professional solutions that demonstrate data engineering, analytics, machine learning, business understanding, and responsible AI where relevant.
- Communicate with me in Dutch unless I request another language.
- Use English for code, variable names, filenames, database objects, commits, and technical documentation unless the existing project uses another convention.

## How we work together

- We work in small steps. One step is one focused change and one commit.
- Before changing files, explain in Dutch what you plan to do and why, and wait for my approval. Skip this only when I explicitly say to go ahead.
- Only touch the files needed for the current step. Do not refactor or "improve" unrelated code.
- Do not commit or push unless I ask. I review changes and commit myself.
- After each step, tell me how to verify it (which command to run, what output to expect) and suggest a short English commit message.
- When a step leads to a technical decision or a problem worth noting, suggest one or two sentences I can add to `docs/logbook.md`. The reflection itself is mine; do not write it for me.

## Project: CrossSellIQ

CrossSellIQ is an individual school project for Cloud & Ops, combined with the Artificial Intelligence course.

The goal is to recommend which new product category an existing H&M customer is likely to buy for the first time within the next 30 days, and to show those recommendations through an API, a web interface, and later an AI agent.

Key definition: a "new category" is a product category the customer has never bought before the reference date. A cross-sell event is the first purchase in such a category within 30 days after the reference date.

The official assignment is `docs/Cloud&Ops_INTRO.pdf`. Check it when requirements are unclear.

### Technology choices

- Python + DuckDB: data pipeline (raw, bronze, silver, gold).
- C# / ASP.NET Core: API and web interface.
- Plain HTML, CSS, and JavaScript in the ASP.NET `wwwroot` folder for the web page. No npm or JavaScript framework unless I decide otherwise (possibly for the optional dashboard in Milestone 4).
- Docker and Docker Compose: containerization (Milestone 2).
- GitHub Actions: CI (Milestone 2) and CD (Milestone 3).
- Azure Container Apps: cloud deployment (Milestone 3).

### Project structure

```
crosssell-iq/
├── backend/            # C# / ASP.NET Core API, web page in wwwroot
├── data/               # data only, never code (not in Git)
│   ├── raw/            # landing zone: original Kaggle CSV files
│   └── crossselliq.duckdb
├── docs/
│   ├── Cloud&Ops_INTRO.pdf # official Cloud & Ops assignment
│   └── logbook.md      # portfolio and logbook (in Dutch)
├── ml/                 # machine learning: training and scoring (Milestone 4)
├── notebooks/          # Jupyter notebooks: pipeline per layer first, and exploration
├── pipeline/           # data engineering: raw -> bronze -> silver -> gold
├── tests/              # C# tests
├── .venv/              # local Python virtual environment (not in Git)
├── requirements.txt    # Python packages needed by the pipeline and ml
├── requirements-dev.txt # development-only packages such as ipykernel
├── AGENTS.md           # same rules as CLAUDE.md, for other AI agents
├── CLAUDE.md
└── README.md
```

- Python runs in `.venv`. Pin versions in `requirements.txt`.
- Run all scripts from the project root, for example `python pipeline/run_pipeline.py`.
- The Git branch is `main`. From Milestone 3 onward, a push to `main` deploys automatically, so `main` must always work and larger changes go through feature branches.

### Data source

Kaggle competition "H&M Personalized Fashion Recommendations" (`h-and-m-personalized-fashion-recommendations`), downloaded with the Kaggle CLI. Only these files are used; the images are not needed:

| File | Size | Rows (approx.) |
|---|---|---|
| `articles.csv` | 36 MB | 105,000 |
| `customers.csv` | 207 MB | 1.4 million |
| `transactions_train.csv` | 3.5 GB | 31.8 million |

Transactions cover roughly September 2018 to September 2020.

Key data facts:

- `customer_id` is a 64-character hexadecimal hash, not a short number. Validate it as such.
- `article_id` has a leading zero and must always be stored as text.
- The product category used for recommendations is `product_group_name`, unless I decide otherwise.

Handling large data:

- Never load `transactions_train.csv` or a full transactions table into pandas or memory. Compute in DuckDB SQL and only convert small results with `.df()`.
- Always use `LIMIT` when inspecting rows.
- Never open the large CSV in an editor or spreadsheet.

### Data pipeline: medallion structure

| Layer | Location | Content |
|---|---|---|
| raw | `data/raw/` | Original files as delivered. Never modify. |
| bronze | schema `bronze` | Data loaded into DuckDB, content unchanged: all columns, all read as `VARCHAR` (`all_varchar`), plus `_source_file` and `_loaded_at`. |
| silver | schema `silver` | Cleaned data: correct types, only needed columns, documented cleaning rules. |
| gold | schema `gold` | Ready-to-use tables for the API and later the model. |

Gold tables for Milestone 1 (baseline only):

- `gold.category_popularity`: per category the number of unique buyers and a normalized popularity score between 0 and 1.
- `gold.customer_categories`: per customer the categories already bought.
- `gold.example_customers`: a small set of real customers with varied purchase histories, for the demo.

Gold tables for Milestone 4 (not before): `gold.cross_sell_events`, `gold.cross_sell_targets`, `gold.training_dataset`, `gold.scoring_dataset`, `gold.model_recommendations`.

Pipeline files:

```
pipeline/
├── raw_to_bronze.py
├── bronze_to_silver.py
├── silver_to_gold.py
├── check_quality.py
└── run_pipeline.py     # runs all steps in order: one command
```

Pipeline rules:

- The pipeline is incremental and idempotent: each run processes only what is new, and running it twice changes nothing the second time.
  - bronze: append per new file. `bronze.load_log` records every loaded file (name, table, row count, load time); files are found by name pattern in `data/raw` (for example `transactions*.csv`). Loading a file and logging it happen in one transaction.
  - silver: `silver.load_log` records every bronze file silver has processed. Transactions are appended (only rows from bronze files not yet processed); customers and articles are upserted with `MERGE ... UPDATE BY NAME / INSERT BY NAME` (SCD1, latest snapshot wins). Never use `UPDATE SET *`, it matches columns by position. If bronze was rebuilt, silver rebuilds itself.
  - gold: `MERGE` (upsert) into every gold table.
  - Each notebook has a `FULL_REFRESH` setting to rebuild its layer from scratch, for example after changing a rule.
- Files are tracked per file, not per row: identical transaction rows are real purchases (no quantity column), so duplicates cannot be detected per row.
- Each step reads only from the previous layer: silver from bronze, gold from silver.
- Silver cleaning rules are decided by me after exploring the data, and documented.
- No SCD2 (history tracking): the source is one static snapshot without change history, so `MERGE` overwrites changed attributes (SCD1). Only add SCD2 if new snapshots start arriving over time and history becomes necessary.
- When Gold model tables are built: use chronological splits only, no information from after the reference date in features, no target columns in the scoring dataset, and the same feature columns in training and scoring.
- The pipeline runs separately and in advance. The API never runs the pipeline; it only reads the result.
- The older `load_database.py` (raw directly to silver) no longer exists; the layered steps above replace it.

### Notebooks versus scripts

- The pipeline is first built in notebooks, one layer at a time, in this order: `01_bronze.ipynb`, `02_silver.ipynb`, `03_gold.ipynb`. A layer is only started after I have approved the previous one.
- Each layer notebook loads its layer incrementally, runs checks against the previous layer (row counts, columns, types), stops with an error if a check fails, and closes the DuckDB connection at the end.
- `notebooks/` is also for exploration: inspecting data, trying queries, finding data problems, and charts.
- `pipeline/` contains the final `.py` scripts. They must run top to bottom with one command, without manual steps. Once a layer works in its notebook, its logic is moved into the matching script (before Milestone 2, because Docker and GitHub Actions run scripts, not notebooks).
- The final pipeline must never depend on a notebook.
- Notebooks must work after "Restart and Run All". Do not print thousands of rows; keep outputs small and meaningful.
- `ipykernel` belongs in `requirements-dev.txt`, not in `requirements.txt`.

### DuckDB

- One database file: `data/crossselliq.duckdb`, with schemas `bronze`, `silver`, and `gold`.
- Only one process can write to the file at a time. The pipeline writes; the API and notebooks must be closed or read-only while the pipeline runs. If a lock error occurs, first check for an open notebook kernel or a running API.
- The API opens the database in read-only mode.
- PostgreSQL is a possible later addition as the API database (decision at Milestone 2). It is not part of Milestone 1.

### API architecture

- Layering: Controller -> Service -> Repository -> database. Controllers never query the database directly.
- Database access sits behind an interface, `IRecommendationRepository`, with a `DuckDbRecommendationRepository` implementation, so a PostgreSQL implementation can be added later without changing services or controllers.
- The API uses only gold tables, never the full transactions.
- The database path comes from configuration (`appsettings.json` or an environment variable), never hardcoded.
- All SQL uses parameters. Never concatenate user input such as `customerId` into SQL.

### Configuration and secrets

- Secrets go in `.env` (not in Git), with a `.env.example` containing only variable names and safe placeholders.
- In GitHub Actions and Azure, secrets go in GitHub Secrets and Azure secrets, never in files.
- Milestone 1 has no secrets yet. Expect the first real secret with the AI agent.
- Keep `.gitignore` up to date: whenever a step creates a new kind of file that must not be in Git (data, database files, secrets, build output, caches, local settings), add it to `.gitignore` in the same step.

### Cloud & Ops milestones (official)

| Deadline | Milestone | Weight | Criteria |
|---|---|---|---|
| 16/10/2026 | 1. Local baseline | 10% | App runs locally with a baseline recommender; clear endpoint returning recommendations; clean code structure; personalization not required yet. |
| 13/11/2026 | 2. Containerization and CI | 10% | `git clone` + one command = full running stack; README is enough to start without help; no secrets in the repository; every push triggers a build in GitHub Actions. |
| 04/12/2026 | 3. Cloud deployment and CI/CD | 10% | Public URL works; push to `main` deploys automatically; I can explain the deployment architecture and cost control (free tier, credits, budget alerts). |
| 18/12/2026 | 4. Personalization and AI agent | 10% | Recommendations are demonstrably personalized; the agent refines recommendations based on user input; I can show baseline versus personalized; portfolio is largely up to date. |

Other grading:

- Portfolio/logbook: 10%. Planning, timesheets (planned versus actual), documented technical choices, proof of learning paths, and reflection.
- Exam: 50%. Live demo of the deployed application, reachable through one URL, with oral explanation and an external jury.

Milestone 2 constraint to keep in mind now: the full data is not in Git, so `git clone` + one command must still produce a working stack. The API depending only on small gold tables is part of the solution.

### Current priority: Milestone 1

Order of work:

1. Pipeline in notebooks, then scripts: raw -> bronze -> silver -> gold baseline tables, and `run_pipeline.py`.
2. C# API: project, `GET /health`, read-only DuckDB connection, repository, baseline service, `GET /api/recommendations/{customerId}`, error handling, tests.
3. Web page in `wwwroot`: input field, example customers, results table.
4. README with setup and run instructions.

Baseline logic: recommend the most popular categories (from `gold.category_popularity`) that the customer has not bought yet (from `gold.customer_categories`), ranked by popularity.

Expected response shape:

```json
{
  "customerId": "<64-character customer hash>",
  "recommendations": [
    {
      "category": "Shoes",
      "score": 0.78,
      "reason": "Popular category this customer has not bought before"
    }
  ]
}
```

- The baseline score is a normalized popularity score. Document its definition in the README. Never present it as a predicted purchase probability.
- Error handling: empty or invalid customer ID (`400`), unknown customer (`404`), customer without purchases in a recommendable category (never bought anything, or only `Unknown` articles; the message must not claim the customer never bought anything), no new categories available, database unreachable.
- Tests: valid customer returns recommendations, unknown customer returns `404`, already-purchased categories are never recommended, results are sorted by score.
- The web page offers real example customer IDs from `gold.example_customers`, so a demo does not depend on typing a hash.

Milestone 1 is done when the pipeline builds the database with one command, the API and web page run locally, the tests pass, and someone else can start everything using only the README.

Do not start Docker, Azure, the machine-learning model, or the AI agent before Milestone 1 works.

### Later milestones

- The personalized model must be compared against the baseline with suitable metrics (for example precision@k and recall@k) on a chronological test period, using techniques from the AI course.
- The AI agent lives inside the same application. It refines recommendations based on user input (for example "only accessories" or "only categories above 70%") and explains them, using only data from the CrossSellIQ API through explicit functions such as `GetCustomerRecommendations`, `FilterRecommendations`, and `ExplainRecommendation`. It must never invent predictions, scores, or explanations. When data is missing, it says so.

Always explain technical choices in Dutch so I can understand and defend the project.

## General working rules

- First inspect the existing project structure, documentation, configuration, and relevant code before making changes.
- Preserve existing work and conventions unless a change is necessary for the request.
- Never invent requirements, data, results, citations, users, testimonials, reviews, metrics, or completed functionality.
- If a missing decision materially affects the result, ask one focused question. Otherwise, make a reasonable assumption and state it briefly.
- Prefer the simplest maintainable solution that fully satisfies the request.
- Do not leave placeholder content, broken links, dead buttons, empty sections, or unfinished TODO items in a completed result.
- Never expose API keys, credentials, tokens, personal data, or secrets. Use environment variables and provide an `.env.example` without real values when needed.
- Validate user input and handle errors with clear, useful messages.
- Keep dependencies limited and justified. Reuse the existing stack where practical.
- Do not make destructive changes or delete user data without explicit permission.
- Keep accessibility, privacy, security, responsive behavior, and performance in scope from the start.

## Accuracy and verification

- Do not claim that something works unless it has been checked.
- After changes, run the most relevant available checks, such as formatting, linting, type checking, tests, builds, database validation, and a focused manual smoke test.
- Check changed files for regressions, inconsistent naming, incorrect imports, unreachable states, and accidental debug output.
- For data work, verify schema, data types, null values, duplicates, join cardinality, date ranges, leakage risk, and metric definitions where relevant.
- For machine-learning work, separate training and evaluation data correctly, establish a baseline, use suitable metrics, document assumptions, and avoid overstating model performance.
- If a check cannot be run, say exactly which check was not run and why.

## Code quality

- Write readable, modular code with descriptive names and small focused functions.
- Add comments only when they explain reasoning, assumptions, or non-obvious behavior.
- Avoid unnecessary abstraction, duplicated logic, giant files, and premature optimization.
- Use deterministic seeds for reproducible data science experiments when appropriate.
- Keep configuration separate from application logic.
- Update relevant documentation whenever setup, behavior, data contracts, or commands change.

## Security requirements

Treat security as a release requirement, not as an optional improvement. Apply the controls that are relevant to the project and verify them before describing the work as production-ready.

### Dependencies and packages

- Identify and remove unused packages only after confirming they are not referenced by source code, scripts, configuration, build tooling, tests, or deployment workflows.
- Update dependencies to supported secure versions. Review release notes and compatibility risks, update lockfiles, and run the relevant tests and build afterward.
- Run the package manager's available vulnerability audit and investigate important findings. Do not claim that all vulnerabilities are fixed when unresolved findings remain.
- Avoid adding a dependency when the existing stack or standard library can solve the problem safely and clearly.

### Secrets and environment variables

- Check tracked files, staged changes, and relevant Git history for exposed credentials, API keys, tokens, passwords, private keys, connection strings, and sensitive configuration.
- Never print or reproduce a discovered secret in terminal output, logs, documentation, commits, or the final response. Redact secret values in reports.
- Never rewrite Git history, rotate credentials, or revoke keys automatically. Report the exposure and request confirmation before destructive history cleanup. Recommend immediate rotation of any exposed credential.
- Keep secrets in environment variables or an approved secret manager. Never embed secrets in source code, client-side bundles, mobile apps, URLs, or public configuration.
- Ensure `.env`, local credential files, private keys, database files, backups, logs, and generated secrets are excluded from Git and from public build output.
- Provide an `.env.example` containing variable names and safe placeholder values only.
- Validate required environment variables at application startup. Fail safely with a clear message when a required value is missing or malformed.
- Separate development, test, staging, and production configuration. Never use production credentials in local development or tests.

### Authentication and passwords

- Use the framework's established authentication and session mechanisms instead of custom cryptography or handwritten token systems.
- Hash passwords with a modern adaptive password-hashing algorithm such as Argon2id, scrypt, or bcrypt using appropriate parameters and a unique salt. Never store plaintext passwords or use MD5, SHA-1, or a single fast hash for password storage.
- Use secure password reset and account verification flows with single-use, short-lived tokens. Do not reveal whether an account exists when that would enable user enumeration.
- Protect sessions and authentication cookies with appropriate `HttpOnly`, `Secure`, and `SameSite` settings. Rotate session identifiers after login and privilege changes.
- Set reasonable session expiration, logout invalidation, login throttling, and protection against credential stuffing and brute-force attempts.
- Add CSRF protection to state-changing requests when authentication relies on cookies.

### Authorization and user access

- Check authentication and authorization separately. A signed-in user must only be able to access resources and actions they are explicitly allowed to use.
- Enforce access control on the server for every protected action. Never rely only on hidden interface elements or client-side route guards.
- Check ownership and tenant boundaries for every resource lookup to prevent insecure direct object reference and cross-tenant access.
- Deny access by default and apply least privilege to users, roles, services, API tokens, and database accounts.
- Protect admin routes with explicit server-side role or permission checks, strong authentication, and auditable sensitive actions.
- Test unauthenticated, ordinary-user, resource-owner, cross-user, and administrator access where applicable.

### API and rate limiting

- Require authentication and authorization on every non-public API endpoint.
- Validate request method, content type, body, query parameters, path parameters, file uploads, and payload size on the server.
- Add rate limiting to authentication, password reset, account creation, search, expensive processing, file upload, public forms, and other abuse-sensitive endpoints.
- Choose rate-limit keys and thresholds appropriate to the endpoint. Consider user, API key, IP address, route, and trusted-proxy configuration. Return a clear `429` response without revealing sensitive information.
- Never trust user-controlled forwarding headers unless the deployment's trusted proxies are configured correctly.
- Use short-lived, scoped API tokens where possible. Do not place sensitive tokens in query strings.
- Return minimal error details to clients and keep sensitive diagnostic information out of API responses.

### Input, forms, XSS, and injection

- Validate all untrusted input on the server using explicit schemas, allowed values, type checks, length limits, and file restrictions. Client-side validation is only a usability enhancement.
- Normalize and sanitize input when the use case requires it, but do not rely on sanitization alone for security.
- Encode output for its destination context and rely on framework auto-escaping to prevent cross-site scripting.
- Avoid rendering raw HTML. If rich HTML is required, sanitize it with a maintained allowlist-based library and test bypass cases.
- Do not use unsafe DOM APIs such as `innerHTML`, `document.write`, or equivalent framework escape hatches with untrusted content.
- Use parameterized SQL or a safe ORM. Never build SQL, shell commands, paths, templates, or code by concatenating untrusted input.
- Protect file uploads with allowlisted types, size limits, generated filenames, non-public storage, malware scanning where appropriate, and authorization on retrieval.

### Browser and transport security

- Configure CORS with an explicit allowlist of trusted origins, required methods, and required headers. Do not combine wildcard origins with credentials.
- Add and verify appropriate security headers, including Content Security Policy, `X-Content-Type-Options`, `Referrer-Policy`, clickjacking protection through CSP `frame-ancestors` or `X-Frame-Options`, and `Strict-Transport-Security` for production HTTPS.
- Use HTTPS in production and do not disable TLS certificate verification.
- Keep the Content Security Policy as restrictive as practical. Avoid `unsafe-inline` and `unsafe-eval` unless a documented constraint makes them temporarily necessary.

### Database and data protection

- Use parameterized queries, least-privileged database accounts, encrypted connections, and separate credentials per environment.
- Never expose the database directly to the public internet unless there is a documented and secured operational requirement.
- Store only necessary data, restrict sensitive fields, and avoid including secrets or personal data in logs.
- Apply authorization filters within database queries where practical, rather than retrieving unauthorized records and filtering them only in application code.
- Use safe migrations, tested backups, and a recovery plan before production database changes.
- Do not use real personal or production data in development or tests unless it has been appropriately minimized and protected.

### Production configuration and exposed files

- Debug mode, development error pages, verbose stack traces, test endpoints, default credentials, and developer tools must be disabled in production.
- Do not expose source maps, `.git`, `.env`, logs, backups, database dumps, configuration files, internal documentation, directory listings, or temporary files through the web server or deployment artifact.
- Ensure production errors shown to users are generic while useful diagnostic details remain in access-controlled server logs.
- Remove temporary accounts, sample credentials, seed administrators, debug routes, mock authentication, and development-only bypasses before release.

### Security audit and verification

- Before a production release, and after security-sensitive changes, perform a focused security audit of dependencies, secrets, authentication, authorization, sessions, APIs, rate limiting, validation, injection risks, XSS, CSRF, CORS, headers, exposed files, database access, logging, and production configuration.
- Prefer established security tooling supported by the project's stack. Treat automated scanning as evidence, not as proof that the application is secure.
- Test controls with negative cases, including unauthorized access, cross-user access, invalid input, oversized requests, repeated requests, missing environment variables, and production configuration.
- Record what was checked, which tools or commands were used, what passed, what remains unresolved, and which checks could not be performed.
- Never state that an application is fully secure. Report the scope and limitations of the audit accurately.

## Data and analytics standards

- Preserve raw source data. Put cleaning and transformations in reproducible scripts, queries, or pipelines.
- Clearly distinguish raw, intermediate, and curated data.
- Document the source, grain, keys, units, time zone, update frequency, and limitations of important datasets.
- Use parameterized SQL and explicit column selection. Avoid `SELECT *` in production queries.
- Prevent train-test leakage and target leakage.
- Use charts only when they help answer a real question. Label axes, units, periods, filters, and data sources clearly.
- Translate technical findings into business implications without implying causation from correlation alone.

## Website and interface design rules

Create interfaces that feel intentional, credible, calm, and professional. Prioritize clear hierarchy, strong typography, useful whitespace, readable content, and predictable interaction.

### Never use

- Purple gradients.
- Pill-shaped buttons. Buttons should use a modest corner radius rather than fully rounded ends.
- Fake reviews, testimonials, ratings, customer logos, partner logos, case studies, user counts, revenue figures, growth percentages, or other invented social proof.
- Vague hero text such as generic claims about revolutionizing, transforming, unlocking, or redefining the future. The hero must state concretely what the product does and for whom.
- Excessive scroll animations, parallax effects, or animation on every section.
- Fake metrics or unsupported numerical claims.
- Em dashes in visible interface copy or user-facing content. Use a comma, colon, semicolon, or full stop instead.
- Emojis in the interface, marketing copy, buttons, navigation, notifications, documentation, or generated content unless I explicitly request them.
- A `Made with AI`, `Built with AI`, AI-generated, or similar badge or tag.
- Decorative elements that imitate functionality.

### Required design behavior

- Use a coherent neutral or brand-appropriate color palette with accessible contrast.
- Use restrained border radii and consistent spacing.
- Use motion only when it communicates state or improves orientation. Respect `prefers-reduced-motion`.
- Make layouts responsive for mobile, tablet, and desktop.
- Provide visible keyboard focus states and semantic HTML.
- Ensure forms have labels, validation feedback, loading states, success states, and error states.
- Every interactive element must perform a real action or be removed.
- Use real project content when it exists. If content is missing, use clearly marked neutral placeholders that do not pretend to be real evidence.

## Required legal pages for websites

Every public-facing website must include:

- A dedicated Privacy Policy page.
- A dedicated Terms and Conditions page.
- Clearly visible footer links to both pages.
- Honest content tailored to the actual website and its real data practices.
- No claim of GDPR or legal compliance unless the implementation and text have been reviewed for that claim.

If the required legal details are unknown, create a clearly marked draft with the missing organization-specific fields identified. Do not invent company names, addresses, contact details, legal bases, processors, retention periods, or jurisdiction.

For CrossSellIQ, these pages are required from Milestone 3 onward, when the application gets a public URL. They are not needed for the local Milestone 1 version.

## Final delivery

- Summarize what changed and where.
- List the checks that passed.
- Mention remaining assumptions, limitations, or manual steps.
- Give exact run or setup commands when relevant.
- Do not describe unfinished work as complete.
