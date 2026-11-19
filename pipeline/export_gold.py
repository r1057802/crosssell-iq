"""Export only the gold schema to a small DuckDB file for the deployed API.

The file is rebuilt from scratch on every run. It is fully derived from gold,
small, and quick to build, so a full rebuild is simpler than an incremental
update and can never keep stale rows. Running it twice gives the same result.
"""

import os
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = PROJECT_ROOT / "data" / "crossselliq.duckdb"
TARGET_PATH = PROJECT_ROOT / "data" / "crossselliq_gold.duckdb"
TEMP_PATH = TARGET_PATH.with_name(TARGET_PATH.name + ".tmp")

# Tables the API reads. The export fails if one of them is missing.
API_TABLES = ("customers", "customer_categories", "category_popularity", "example_customers")


def remove_database_file(path):
    for candidate in (path, path.with_name(path.name + ".wal")):
        candidate.unlink(missing_ok=True)


def quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def duckdb_string(path):
    return "'" + str(path).replace("'", "''") + "'"


def gold_tables(con, catalog):
    rows = con.execute(
        """
        SELECT table_name
        FROM duckdb_tables()
        WHERE database_name = $catalog AND schema_name = 'gold'
        ORDER BY table_name
        """,
        {"catalog": catalog},
    ).fetchall()
    return [row[0] for row in rows]


def primary_key_columns(con, catalog, table):
    row = con.execute(
        """
        SELECT constraint_column_names
        FROM duckdb_constraints()
        WHERE database_name = $catalog AND schema_name = 'gold'
          AND table_name = $table AND constraint_type = 'PRIMARY KEY'
        """,
        {"catalog": catalog, "table": table},
    ).fetchone()
    return row[0] if row else []


def row_count(con, catalog, table):
    return con.execute(f"SELECT count(*) FROM {quote(catalog)}.gold.{quote(table)}").fetchone()[0]


def main():
    if not SOURCE_PATH.exists():
        raise FileNotFoundError(f"Database not found: {SOURCE_PATH}. Run python pipeline/run_pipeline.py first.")

    remove_database_file(TEMP_PATH)
    con = duckdb.connect(str(TEMP_PATH))
    try:
        con.execute(f"ATTACH {duckdb_string(SOURCE_PATH)} AS source (READ_ONLY)")
        target_catalog = con.execute("SELECT current_database()").fetchone()[0]

        source_tables = gold_tables(con, "source")
        missing = [name for name in API_TABLES if name not in source_tables]
        if missing:
            raise RuntimeError(f"Missing gold tables: {missing}. Run python pipeline/run_pipeline.py first.")

        print(f"Source: {SOURCE_PATH}")
        con.execute("CREATE SCHEMA gold")
        for table in source_tables:
            # The exported file is read-only, so primary key indexes are left out: they tripled
            # the file size. Rows are sorted by the primary key instead, which lets DuckDB skip
            # most of the data when the API looks up one customer.
            key_columns = primary_key_columns(con, "source", table)
            order_by = " ORDER BY " + ", ".join(quote(column) for column in key_columns) if key_columns else ""
            con.execute(
                f"CREATE TABLE gold.{quote(table)} AS SELECT * FROM source.gold.{quote(table)}{order_by}"
            )

        print("Checks")
        failures = []
        if set(gold_tables(con, target_catalog)) != set(source_tables):
            failures.append("the exported file has a different set of gold tables")
        for table in source_tables:
            source_rows = row_count(con, "source", table)
            target_rows = row_count(con, target_catalog, table)
            passed = source_rows == target_rows
            print(f"  {'OK  ' if passed else 'FAIL'} gold.{table}: {target_rows:,} rows")
            if not passed:
                failures.append(f"gold.{table} has {target_rows:,} rows instead of {source_rows:,}")
        if failures:
            raise RuntimeError("Export check failed: " + "; ".join(failures))

        con.execute("DETACH source")
        con.execute("CHECKPOINT")
    except BaseException:
        con.close()
        remove_database_file(TEMP_PATH)
        raise
    con.close()

    # Replace the old file only after every check passed, so a half-written file is never left behind.
    remove_database_file(TARGET_PATH)
    os.replace(TEMP_PATH, TARGET_PATH)
    size_mb = TARGET_PATH.stat().st_size / 1_000_000
    print(f"Exported: {TARGET_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
