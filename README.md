# CrossSellIQ

CrossSellIQ is a school project for recommending product categories an existing H&M customer has not bought before. The current data pipeline builds the local baseline tables in DuckDB. The API and web interface are later Milestone 1 steps.

## Run the data pipeline

Use Python with the dependencies pinned in `requirements.txt`. From the project root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Place the original Kaggle H&M CSV files `articles.csv`, `customers.csv`, and `transactions_train.csv` in `data/raw/`. These files and the generated database are local data and are excluded from Git. Then run:

```powershell
.venv\Scripts\python.exe pipeline\run_pipeline.py
```

The command runs Bronze, Silver, and Gold in order. It processes new files incrementally, skips unchanged input, and runs the layer checks. The database is `data/crossselliq.duckdb`. Close notebook kernels or other DuckDB writers before running the pipeline.

To validate an existing database without changing it:

```powershell
.venv\Scripts\python.exe pipeline\check_quality.py
```

Each layer can also be run separately with `pipeline\raw_to_bronze.py`, `pipeline\bronze_to_silver.py`, or `pipeline\silver_to_gold.py`. Use `--full-refresh` only when you intend to rebuild a layer or the entire pipeline from the source data.

`gold.category_popularity.popularity_score` is the category's unique buyer count divided by the largest category's unique buyer count. It ranges from 0 to 1 and is **not** a predicted purchase probability.
