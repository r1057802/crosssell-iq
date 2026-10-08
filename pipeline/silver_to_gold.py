"""Build the gold layer from the reviewed 03_gold.ipynb logic."""

import argparse
import time
from pathlib import Path

import duckdb

from check_quality import check_gold


def main(full_refresh=False):
    con = None
    try:
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        DB_PATH = PROJECT_ROOT / "data" / "crossselliq.duckdb"
        if not DB_PATH.exists():
            raise FileNotFoundError(f"Database not found: {DB_PATH}. Run python pipeline/raw_to_bronze.py first.")

        con = duckdb.connect(str(DB_PATH))

        def table_exists(schema, table):
            return con.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = $schema AND table_name = $table",
                {"schema": schema, "table": table},
            ).fetchone()[0] == 1

        required = ("customers", "articles", "transactions", "load_log")
        missing = [name for name in required if not table_exists("silver", name)]
        if missing:
            raise RuntimeError(f"Missing Silver tables: {missing}. Run python pipeline/bronze_to_silver.py first.")

        print(f"Database: {DB_PATH}")

        con.execute("CREATE SCHEMA IF NOT EXISTS gold")

        DDL = {
            "customers": """
                CREATE TABLE IF NOT EXISTS gold.customers (
                    customer_id VARCHAR PRIMARY KEY
                )""",
            "customer_categories": """
                CREATE TABLE IF NOT EXISTS gold.customer_categories (
                    customer_id VARCHAR NOT NULL,
                    category VARCHAR NOT NULL,
                    first_purchase_date DATE NOT NULL,
                    purchase_count BIGINT NOT NULL,
                    PRIMARY KEY (customer_id, category)
                )""",
            "category_popularity": """
                CREATE TABLE IF NOT EXISTS gold.category_popularity (
                    category VARCHAR PRIMARY KEY,
                    unique_buyers BIGINT NOT NULL,
                    popularity_score DOUBLE NOT NULL
                )""",
            "example_customers": """
                CREATE TABLE IF NOT EXISTS gold.example_customers (
                    customer_id VARCHAR PRIMARY KEY,
                    purchased_category_count BIGINT NOT NULL
                )""",
            "source_log": """
                CREATE TABLE IF NOT EXISTS gold.source_log (
                    file_name VARCHAR PRIMARY KEY,
                    table_name VARCHAR NOT NULL,
                    silver_processed_at TIMESTAMP NOT NULL,
                    row_count BIGINT NOT NULL
                )""",
        }
        for ddl in DDL.values():
            con.execute(ddl)

        source_difference = con.execute("""
            SELECT count(*) FROM (
                (SELECT file_name, table_name, processed_at, row_count FROM silver.load_log
                 EXCEPT
                 SELECT file_name, table_name, silver_processed_at, row_count FROM gold.source_log)
                UNION ALL
                (SELECT file_name, table_name, silver_processed_at, row_count FROM gold.source_log
                 EXCEPT
                 SELECT file_name, table_name, processed_at, row_count FROM silver.load_log)
            )
        """).fetchone()[0]
        gold_empty = any(con.execute(f"SELECT count(*) FROM gold.{name}").fetchone()[0] == 0
                         for name in ("customers", "customer_categories", "category_popularity", "example_customers"))
        refresh_needed = full_refresh or source_difference > 0 or gold_empty
        print(f"Silver/Gold source-log differences: {source_difference}")
        print(f"Gold refresh needed: {refresh_needed}")

        if refresh_needed:
            started = time.perf_counter()
            con.begin()
            try:
                con.execute("""
                    CREATE OR REPLACE TEMP TABLE stage_customers AS
                    SELECT customer_id FROM silver.customers
                """)
                con.execute("""
                    CREATE OR REPLACE TEMP TABLE stage_customer_categories AS
                    SELECT
                        t.customer_id,
                        a.product_group_name AS category,
                        min(t.transaction_date) AS first_purchase_date,
                        count(*) AS purchase_count
                    FROM silver.transactions t
                    JOIN silver.articles a USING (article_id)
                    WHERE a.product_group_name IS NOT NULL
                      AND trim(a.product_group_name) <> ''
                      AND a.product_group_name <> 'Unknown'
                    GROUP BY t.customer_id, a.product_group_name
                """)
                con.execute("""
                    CREATE OR REPLACE TEMP TABLE stage_category_popularity AS
                    WITH categories AS (
                        SELECT DISTINCT product_group_name AS category
                        FROM silver.articles
                        WHERE product_group_name IS NOT NULL
                          AND trim(product_group_name) <> ''
                          AND product_group_name <> 'Unknown'
                    ),
                    buyers AS (
                        SELECT category, count(*) AS unique_buyers
                        FROM stage_customer_categories
                        GROUP BY category
                    ),
                    counts AS (
                        SELECT c.category, coalesce(b.unique_buyers, 0) AS unique_buyers
                        FROM categories c
                        LEFT JOIN buyers b USING (category)
                    )
                    SELECT
                        category,
                        unique_buyers,
                        CASE WHEN max(unique_buyers) OVER () = 0 THEN 0.0
                             ELSE unique_buyers::DOUBLE / max(unique_buyers) OVER ()
                        END AS popularity_score
                    FROM counts
                """)
                con.execute("""
                    CREATE OR REPLACE TEMP TABLE stage_example_customers AS
                    WITH counts AS (
                        SELECT c.customer_id, coalesce(b.purchased_category_count, 0) AS purchased_category_count
                        FROM stage_customers c
                        LEFT JOIN (
                            SELECT customer_id, count(*) AS purchased_category_count
                            FROM stage_customer_categories
                            GROUP BY customer_id
                        ) b USING (customer_id)
                    )
                    SELECT customer_id, purchased_category_count
                    FROM counts
                    QUALIFY row_number() OVER (
                        PARTITION BY CASE
                            WHEN purchased_category_count = 0 THEN 0
                            WHEN purchased_category_count = 1 THEN 1
                            WHEN purchased_category_count <= 3 THEN 2
                            ELSE 3
                        END
                        ORDER BY customer_id
                    ) <= 3
                """)
                for name in ("example_customers", "customer_categories", "category_popularity", "customers"):
                    con.execute(f"DELETE FROM gold.{name}")
                for name, key in (
                    ("customers", "target.customer_id = source.customer_id"),
                    ("customer_categories", "target.customer_id = source.customer_id AND target.category = source.category"),
                    ("category_popularity", "target.category = source.category"),
                    ("example_customers", "target.customer_id = source.customer_id"),
                ):
                    con.execute(f"""
                        MERGE INTO gold.{name} AS target
                        USING stage_{name} AS source
                        ON {key}
                        WHEN MATCHED THEN UPDATE BY NAME
                        WHEN NOT MATCHED THEN INSERT BY NAME
                    """)
                con.execute("DELETE FROM gold.source_log")
                con.execute("""
                    INSERT INTO gold.source_log (file_name, table_name, silver_processed_at, row_count)
                    SELECT file_name, table_name, processed_at, row_count
                    FROM silver.load_log
                """)
                con.commit()
            except Exception:
                con.rollback()
                raise
            print(f"Gold refreshed in {time.perf_counter() - started:.1f} s")
        else:
            print("No Silver changes: Gold is already up to date.")

        check_gold(con)
    finally:
        if con is not None:
            con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-refresh", action="store_true", help="Rebuild this layer from scratch")
    args = parser.parse_args()
    main(full_refresh=args.full_refresh)
