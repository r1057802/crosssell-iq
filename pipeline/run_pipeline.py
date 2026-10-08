"""Run the incremental Bronze, Silver, and Gold pipeline in order."""

import argparse

from bronze_to_silver import main as build_silver
from raw_to_bronze import main as build_bronze
from silver_to_gold import main as build_gold


def main(full_refresh=False):
    print("=== Bronze ===", flush=True)
    build_bronze(full_refresh=full_refresh)
    print("=== Silver ===", flush=True)
    build_silver(full_refresh=full_refresh)
    print("=== Gold ===", flush=True)
    build_gold(full_refresh=full_refresh)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-refresh", action="store_true", help="Rebuild every layer from scratch")
    args = parser.parse_args()
    main(full_refresh=args.full_refresh)
