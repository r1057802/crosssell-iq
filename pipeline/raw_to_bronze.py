"""Build the bronze layer from the reviewed 01_bronze.ipynb logic."""

import argparse
import time
from pathlib import Path

import duckdb

from check_quality import check_bronze


def main(full_refresh=False):
    con = None
    try:
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        RAW_DIR = PROJECT_ROOT / "data" / "raw"
        DB_PATH = PROJECT_ROOT / "data" / "crossselliq.duckdb"

        # Bronze table name -> file name pattern in data/raw.
        SOURCE_PATTERNS = {
            "articles": "articles*.csv",
            "customers": "customers*.csv",
            "transactions": "transactions*.csv",
        }
        METADATA_COLUMNS = ["_source_file", "_loaded_at"]

        source_files = [
            (table_name, path)
            for table_name, pattern in SOURCE_PATTERNS.items()
            for path in sorted(RAW_DIR.glob(pattern))
        ]

        missing_tables = [t for t in SOURCE_PATTERNS if t not in {table for table, _ in source_files}]
        if missing_tables:
            raise FileNotFoundError(f"No raw file found for: {missing_tables} in {RAW_DIR}")

        print(f"Raw folder: {RAW_DIR}")
        print(f"Database:   {DB_PATH}")
        for table_name, path in source_files:
            print(f"  found {path.name} -> bronze.{table_name}")

        con = duckdb.connect(str(DB_PATH))
        con.execute("CREATE SCHEMA IF NOT EXISTS bronze")

        load_log_exists = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'bronze' AND table_name = 'load_log'"
        ).fetchone()[0] == 1

        if full_refresh or not load_log_exists:
            reason = "--full-refresh was requested" if full_refresh else "no load log found"
            print(f"Rebuilding bronze from scratch ({reason}).")
            # Table names come from the fixed SOURCE_PATTERNS mapping, not from user input.
            for table_name in [*SOURCE_PATTERNS, "load_log"]:
                con.execute(f"DROP TABLE IF EXISTS bronze.{table_name}")

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS bronze.load_log (
                file_name  VARCHAR PRIMARY KEY,
                table_name VARCHAR NOT NULL,
                row_count  BIGINT NOT NULL,
                loaded_at  TIMESTAMP NOT NULL
            )
            """
        )

        already_loaded = {row[0] for row in con.execute("SELECT file_name FROM bronze.load_log").fetchall()}
        new_files = [(table_name, path) for table_name, path in source_files if path.name not in already_loaded]

        print(f"Files already loaded: {len(already_loaded)}")
        print(f"New files to load:    {len(new_files)}")

        # current_timestamp is fixed for the duration of a transaction, so the rows and their
        # load log entry get exactly the same _loaded_at value.
        SELECT_FILE_SQL = """
            SELECT
                *,
                $file_name AS _source_file,
                current_timestamp AT TIME ZONE 'UTC' AS _loaded_at
            FROM read_csv($path, header = true, all_varchar = true)
        """


        def load_file(con, table_name, path):
            """Append one raw file to its bronze table and record it in the load log, atomically."""
            params = {"path": str(path), "file_name": path.name}
            con.begin()
            try:
                # The table name comes from the fixed SOURCE_PATTERNS mapping, and identifiers
                # cannot be SQL parameters. The file path and name are passed as parameters.
                con.execute(f"CREATE TABLE IF NOT EXISTS bronze.{table_name} AS {SELECT_FILE_SQL} LIMIT 0", params)
                row_count = con.execute(f"INSERT INTO bronze.{table_name} BY NAME {SELECT_FILE_SQL}", params).fetchone()[0]
                con.execute(
                    """
                    INSERT INTO bronze.load_log (file_name, table_name, row_count, loaded_at)
                    VALUES ($file_name, $table_name, $row_count, current_timestamp AT TIME ZONE 'UTC')
                    """,
                    {"file_name": path.name, "table_name": table_name, "row_count": row_count},
                )
                con.commit()
            except Exception:
                con.rollback()
                raise
            return row_count


        if not new_files:
            print("No new files: bronze is up to date.")

        for table_name, path in new_files:
            start = time.perf_counter()
            row_count = load_file(con, table_name, path)
            print(f"{path.name:<24} -> bronze.{table_name:<13} {row_count:>12,} rows in {time.perf_counter() - start:.1f} s")

        check_bronze(con, source_files, SOURCE_PATTERNS, METADATA_COLUMNS)
    finally:
        if con is not None:
            con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-refresh", action="store_true", help="Rebuild this layer from scratch")
    args = parser.parse_args()
    main(full_refresh=args.full_refresh)
