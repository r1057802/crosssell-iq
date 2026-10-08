"""Build the silver layer from the reviewed 02_silver.ipynb logic."""

import argparse
import time
from pathlib import Path

import duckdb

from check_quality import check_silver


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


        if not table_exists("bronze", "load_log"):
            raise RuntimeError("bronze.load_log not found. Run python pipeline/raw_to_bronze.py first.")

        print(f"Database: {DB_PATH}")

        SILVER_TABLES_DDL = {
            "customers": """
                CREATE TABLE IF NOT EXISTS silver.customers (
                    customer_id            VARCHAR PRIMARY KEY,
                    fn                     BOOLEAN,
                    active                 BOOLEAN,
                    club_member_status     VARCHAR,
                    fashion_news_frequency VARCHAR,
                    age                    INTEGER
                )""",
            "articles": """
                CREATE TABLE IF NOT EXISTS silver.articles (
                    article_id         VARCHAR PRIMARY KEY,
                    product_code       VARCHAR,
                    prod_name          VARCHAR,
                    product_type_name  VARCHAR,
                    product_group_name VARCHAR,
                    colour_group_name  VARCHAR,
                    department_name    VARCHAR,
                    index_group_name   VARCHAR,
                    section_name       VARCHAR,
                    garment_group_name VARCHAR
                )""",
            "transactions": """
                CREATE TABLE IF NOT EXISTS silver.transactions (
                    transaction_date DATE NOT NULL,
                    customer_id      VARCHAR NOT NULL,
                    article_id       VARCHAR NOT NULL,
                    price            DOUBLE,
                    sales_channel_id TINYINT
                )""",
        }

        LOAD_LOG_DDL = """
            CREATE TABLE IF NOT EXISTS silver.load_log (
                file_name        VARCHAR PRIMARY KEY,
                table_name       VARCHAR NOT NULL,
                bronze_loaded_at TIMESTAMP NOT NULL,
                row_count        BIGINT NOT NULL,
                processed_at     TIMESTAMP NOT NULL
            )"""

        con.execute("CREATE SCHEMA IF NOT EXISTS silver")

        rebuild_reason = None
        if full_refresh:
            rebuild_reason = "--full-refresh was requested"
        elif not table_exists("silver", "load_log"):
            rebuild_reason = "no silver load log found"
        else:
            reloaded_in_bronze = con.execute(
                """
                SELECT count(*)
                FROM silver.load_log s
                LEFT JOIN bronze.load_log b USING (file_name)
                WHERE b.loaded_at IS DISTINCT FROM s.bronze_loaded_at
                """
            ).fetchone()[0]
            if reloaded_in_bronze:
                rebuild_reason = f"{reloaded_in_bronze} file(s) were reloaded or removed in bronze"

        if rebuild_reason:
            print(f"Rebuilding silver from scratch ({rebuild_reason}).")
            # Table names come from the fixed SILVER_TABLES_DDL mapping, not from user input.
            for table_name in [*SILVER_TABLES_DDL, "load_log"]:
                con.execute(f"DROP TABLE IF EXISTS silver.{table_name}")

        for ddl in [*SILVER_TABLES_DDL.values(), LOAD_LOG_DDL]:
            con.execute(ddl)

        new_files = con.execute(
            """
            SELECT b.file_name, b.table_name, b.loaded_at
            FROM bronze.load_log b
            ANTI JOIN silver.load_log s USING (file_name)
            ORDER BY b.loaded_at, b.file_name
            """
        ).fetchall()

        print(f"Bronze files already in silver: {con.execute('SELECT count(*) FROM silver.load_log').fetchone()[0]}")
        print(f"New bronze files to process:    {len(new_files)}")

        CLEANED_CUSTOMERS_SQL = """
            SELECT
                customer_id,
                CASE WHEN FN = '1.0' THEN TRUE END AS fn,
                CASE WHEN Active = '1.0' THEN TRUE END AS active,
                club_member_status,
                CASE
                    WHEN fashion_news_frequency = 'None' THEN 'NONE'
                    ELSE fashion_news_frequency
                END AS fashion_news_frequency,
                CAST(age AS INTEGER) AS age
            FROM bronze.customers
            WHERE _source_file = $file_name
        """

        CLEANED_ARTICLES_SQL = """
            SELECT
                article_id,
                product_code,
                prod_name,
                product_type_name,
                product_group_name,
                colour_group_name,
                department_name,
                index_group_name,
                section_name,
                garment_group_name
            FROM bronze.articles
            WHERE _source_file = $file_name
        """

        CLEANED_TRANSACTIONS_SQL = """
            SELECT
                CAST(t_dat AS DATE) AS transaction_date,
                customer_id,
                article_id,
                CAST(price AS DOUBLE) AS price,
                CAST(sales_channel_id AS TINYINT) AS sales_channel_id
            FROM bronze.transactions
            WHERE _source_file = $file_name
        """


        def merge_sql(table_name, key, cleaned_sql):
            return f"""
                MERGE INTO silver.{table_name} AS target
                USING ({cleaned_sql}) AS source
                ON target.{key} = source.{key}
                WHEN MATCHED THEN UPDATE BY NAME
                WHEN NOT MATCHED THEN INSERT BY NAME
            """


        # Transactions are appended in date order, so DuckDB can skip data quickly when filtering on a period.
        PROCESS_SQL = {
            "customers": merge_sql("customers", "customer_id", CLEANED_CUSTOMERS_SQL),
            "articles": merge_sql("articles", "article_id", CLEANED_ARTICLES_SQL),
            "transactions": f"INSERT INTO silver.transactions BY NAME {CLEANED_TRANSACTIONS_SQL} ORDER BY transaction_date",
        }


        def process_file(con, file_name, table_name, bronze_loaded_at):
            """Process one bronze file into silver and record it in the silver load log, atomically."""
            con.begin()
            try:
                row_count = con.execute(PROCESS_SQL[table_name], {"file_name": file_name}).fetchone()[0]
                con.execute(
                    """
                    INSERT INTO silver.load_log (file_name, table_name, bronze_loaded_at, row_count, processed_at)
                    VALUES ($file_name, $table_name, $bronze_loaded_at, $row_count, current_timestamp AT TIME ZONE 'UTC')
                    """,
                    {
                        "file_name": file_name,
                        "table_name": table_name,
                        "bronze_loaded_at": bronze_loaded_at,
                        "row_count": row_count,
                    },
                )
                con.commit()
            except Exception:
                con.rollback()
                raise
            return row_count


        if not new_files:
            print("No new bronze files: silver is up to date.")

        for file_name, table_name, bronze_loaded_at in new_files:
            start = time.perf_counter()
            row_count = process_file(con, file_name, table_name, bronze_loaded_at)
            method = "appended" if table_name == "transactions" else "merged"
            print(f"{file_name:<24} -> silver.{table_name:<13} {row_count:>12,} rows {method} in {time.perf_counter() - start:.1f} s")

        check_silver(con)
    finally:
        if con is not None:
            con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-refresh", action="store_true", help="Rebuild this layer from scratch")
    args = parser.parse_args()
    main(full_refresh=args.full_refresh)
