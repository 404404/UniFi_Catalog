#!/usr/bin/env python3
"""Validate all source catalog files and optionally the checked-in index."""

from __future__ import annotations

import argparse
from pathlib import Path

from catalog import CatalogError, check_generated_index, validate_catalog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check-generated", action="store_true")
    args = parser.parse_args()
    try:
        models, _, _ = validate_catalog(args.root)
        if args.check_generated:
            check_generated_index(args.root, models)
    except CatalogError as exc:
        print(f"CATALOG_VALIDATION=FAIL: {exc}")
        return 1
    print(f"CATALOG_VALIDATION=PASS model_count={len(models)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
