"""Validation checks from the three layer notebooks."""

from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "crossselliq.duckdb"


def check_bronze(con, source_files, source_patterns, metadata_columns):
    SOURCE_PATTERNS = source_patterns
    METADATA_COLUMNS = metadata_columns
    results = []


    def check(name, passed):
        results.append((name, passed))
        print(f"  {'OK  ' if passed else 'FAIL'} {name}")


    def scalar(sql, params=None):
        return con.execute(sql, params or {}).fetchone()[0]


    logged = {row[0]: row[1] for row in con.execute("SELECT file_name, row_count FROM bronze.load_log").fetchall()}

    print("load log")
    check("every raw file is in the load log", all(path.name in logged for _, path in source_files))

    for table_name, path in source_files:
        raw_rows = scalar("SELECT count(*) FROM read_csv($path, header = true, all_varchar = true)", {"path": str(path)})
        bronze_rows = scalar(f"SELECT count(*) FROM bronze.{table_name} WHERE _source_file = $file_name", {"file_name": path.name})
        print(f"{path.name}: {bronze_rows:,} rows in bronze.{table_name}")
        check("rows match the CSV file", bronze_rows == raw_rows)
        check("rows match the load log", bronze_rows == logged.get(path.name))

    for table_name in SOURCE_PATTERNS:
        print(f"bronze.{table_name}")
        orphan_rows = scalar(
            f"SELECT count(*) FROM bronze.{table_name} WHERE _source_file NOT IN (SELECT file_name FROM bronze.load_log)"
        )
        check("every row belongs to a logged file", orphan_rows == 0)

        first_file = next(path for t, path in source_files if t == table_name)
        raw_columns = [
            row[0]
            for row in con.execute(
                "DESCRIBE SELECT * FROM read_csv($path, header = true, all_varchar = true)", {"path": str(first_file)}
            ).fetchall()
        ]
        bronze_schema = con.execute(f"DESCRIBE bronze.{table_name}").fetchall()
        check("columns match the CSV + metadata", [row[0] for row in bronze_schema] == raw_columns + METADATA_COLUMNS)
        check("all source columns are VARCHAR",
              all(row[1] == "VARCHAR" for row in bronze_schema if row[0] not in METADATA_COLUMNS))

    failed = [name for name, passed in results if not passed]
    if failed:
        raise AssertionError(f"{len(failed)} bronze check(s) failed: {failed}")
    print(f"All {len(results)} bronze checks passed.")


def check_silver(con):
    EXPECTED_SCHEMAS = {
        "customers": {
            "customer_id": "VARCHAR",
            "fn": "BOOLEAN",
            "active": "BOOLEAN",
            "club_member_status": "VARCHAR",
            "fashion_news_frequency": "VARCHAR",
            "age": "INTEGER",
        },
        "articles": {
            "article_id": "VARCHAR",
            "product_code": "VARCHAR",
            "prod_name": "VARCHAR",
            "product_type_name": "VARCHAR",
            "product_group_name": "VARCHAR",
            "colour_group_name": "VARCHAR",
            "department_name": "VARCHAR",
            "index_group_name": "VARCHAR",
            "section_name": "VARCHAR",
            "garment_group_name": "VARCHAR",
        },
        "transactions": {
            "transaction_date": "DATE",
            "customer_id": "VARCHAR",
            "article_id": "VARCHAR",
            "price": "DOUBLE",
            "sales_channel_id": "TINYINT",
        },
    }
    KEYS = {"customers": "customer_id", "articles": "article_id"}

    results = []


    def check(name, passed):
        results.append((name, passed))
        print(f"  {'OK  ' if passed else 'FAIL'} {name}")


    def scalar(sql):
        return con.execute(sql).fetchone()[0]


    print("load log")
    check("every bronze file is processed into silver",
          scalar("SELECT count(*) FROM bronze.load_log ANTI JOIN silver.load_log USING (file_name)") == 0)

    # Table and key names come from the fixed mappings above, not from user input.
    for table_name, expected_schema in EXPECTED_SCHEMAS.items():
        silver_rows = scalar(f"SELECT count(*) FROM silver.{table_name}")
        if table_name == "transactions":
            expected_rows = scalar("SELECT count(*) FROM bronze.transactions")
            rule = "row count matches bronze"
        else:
            expected_rows = scalar(f"SELECT count(DISTINCT {KEYS[table_name]}) FROM bronze.{table_name}")
            rule = f"one row per unique {KEYS[table_name]} in bronze"
        actual_schema = {row[0]: row[1] for row in con.execute(f"DESCRIBE silver.{table_name}").fetchall()}

        print(f"silver.{table_name}: {silver_rows:,} rows")
        check(rule, silver_rows == expected_rows)
        check("columns and types as expected", actual_schema == expected_schema)

    check("appended transaction rows match the silver load log",
          scalar("SELECT count(*) FROM silver.transactions")
          == scalar("SELECT coalesce(sum(row_count), 0) FROM silver.load_log WHERE table_name = 'transactions'"))

    print("keys")
    check("customer_id is a 64-character hex hash",
          scalar("SELECT count(*) FROM silver.customers WHERE NOT regexp_full_match(customer_id, '[0-9a-f]{64}')") == 0)
    check("transaction keys and date never empty",
          scalar("""SELECT count(*) FROM silver.transactions
                    WHERE transaction_date IS NULL OR customer_id IS NULL OR article_id IS NULL""") == 0)

    print("relationships")
    check("every transaction has a known customer",
          scalar("SELECT count(*) FROM silver.transactions ANTI JOIN silver.customers USING (customer_id)") == 0)
    check("every transaction has a known article",
          scalar("SELECT count(*) FROM silver.transactions ANTI JOIN silver.articles USING (article_id)") == 0)

    print("cleaning rules")
    check("fn and active match the latest bronze snapshot",
          scalar("""
              WITH latest AS (
                  SELECT customer_id, FN, Active
                  FROM bronze.customers
                  QUALIFY row_number() OVER (PARTITION BY customer_id ORDER BY _loaded_at DESC) = 1
              )
              SELECT count(*)
              FROM silver.customers s
              JOIN latest b USING (customer_id)
              WHERE coalesce(b.FN = '1.0', FALSE) <> (s.fn IS NOT NULL)
                 OR coalesce(b.Active = '1.0', FALSE) <> (s.active IS NOT NULL)
          """) == 0)
    check("fn and active only TRUE or NULL",
          scalar("SELECT count(*) FROM silver.customers WHERE fn = FALSE OR active = FALSE") == 0)
    check("fashion_news_frequency only NONE, Regularly, Monthly or NULL",
          scalar("""SELECT count(*) FROM silver.customers
                    WHERE fashion_news_frequency NOT IN ('NONE', 'Regularly', 'Monthly')""") == 0)
    check("sales_channel_id only 1 or 2",
          scalar("SELECT count(*) FROM silver.transactions WHERE sales_channel_id NOT IN (1, 2)") == 0)
    check("price always positive",
          scalar("SELECT count(*) FROM silver.transactions WHERE price <= 0") == 0)

    failed = [name for name, passed in results if not passed]
    if failed:
        raise AssertionError(f"{len(failed)} silver check(s) failed: {failed}")
    print(f"All {len(results)} silver checks passed.")


def check_gold(con):
    results = []

    def check(name, passed):
        results.append((name, passed))
        print(f"  {'OK  ' if passed else 'FAIL'} {name}")

    def scalar(sql):
        return con.execute(sql).fetchone()[0]

    check("all Silver customers are in Gold",
          scalar("SELECT count(*) FROM gold.customers") == scalar("SELECT count(*) FROM silver.customers"))
    check("Gold customer IDs are valid hashes",
          scalar("SELECT count(*) FROM gold.customers WHERE NOT regexp_full_match(customer_id, '[0-9a-f]{64}')") == 0)
    check("all customer-category buyers are known",
          scalar("SELECT count(*) FROM gold.customer_categories ANTI JOIN gold.customers USING (customer_id)") == 0)
    check("all customer-category values are known",
          scalar("SELECT count(*) FROM gold.customer_categories ANTI JOIN gold.category_popularity USING (category)") == 0)
    check("no unknown or empty categories",
          scalar("""SELECT count(*) FROM gold.category_popularity
                    WHERE category IS NULL OR trim(category) = '' OR category = 'Unknown'""") == 0)
    check("positive purchase counts and valid first dates",
          scalar("""SELECT count(*) FROM gold.customer_categories
                    WHERE purchase_count <= 0 OR first_purchase_date IS NULL""") == 0)
    check("popularity buyer counts match customer-category rows",
          scalar("""SELECT count(*) FROM gold.category_popularity p
                    LEFT JOIN (
                        SELECT category, count(*) AS buyers
                        FROM gold.customer_categories GROUP BY category
                    ) b USING (category)
                    WHERE p.unique_buyers <> coalesce(b.buyers, 0)""") == 0)
    check("popularity scores are normalized",
          scalar("""SELECT count(*) FROM gold.category_popularity
                    WHERE popularity_score < 0 OR popularity_score > 1 OR NOT isfinite(popularity_score)""") == 0
          and scalar("SELECT max(popularity_score) FROM gold.category_popularity") == 1.0)
    check("example customers are real and have correct counts",
          scalar("""SELECT count(*) FROM gold.example_customers e
                    LEFT JOIN gold.customers c USING (customer_id)
                    LEFT JOIN (
                        SELECT customer_id, count(*) AS category_count
                        FROM gold.customer_categories GROUP BY customer_id
                    ) b USING (customer_id)
                    WHERE c.customer_id IS NULL
                       OR e.purchased_category_count <> coalesce(b.category_count, 0)""") == 0)
    check("Gold source log matches Silver",
          scalar("""SELECT count(*) FROM (
                      (SELECT file_name, table_name, processed_at, row_count FROM silver.load_log
                       EXCEPT SELECT file_name, table_name, silver_processed_at, row_count FROM gold.source_log)
                      UNION ALL
                      (SELECT file_name, table_name, silver_processed_at, row_count FROM gold.source_log
                       EXCEPT SELECT file_name, table_name, processed_at, row_count FROM silver.load_log)
                    )""") == 0)
    failed = [name for name, passed in results if not passed]
    if failed:
        raise AssertionError(f"{len(failed)} Gold check(s) failed: {failed}")
    print(f"All {len(results)} Gold checks passed.")


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    source_patterns = {
        "articles": "articles*.csv",
        "customers": "customers*.csv",
        "transactions": "transactions*.csv",
    }
    raw_dir = PROJECT_ROOT / "data" / "raw"
    source_files = [
        (table_name, path)
        for table_name, pattern in source_patterns.items()
        for path in sorted(raw_dir.glob(pattern))
    ]
    missing = [name for name in source_patterns if name not in {table for table, _ in source_files}]
    if missing:
        raise FileNotFoundError(f"No raw file found for: {missing} in {raw_dir}")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        check_bronze(con, source_files, source_patterns, ["_source_file", "_loaded_at"])
        check_silver(con)
        check_gold(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
