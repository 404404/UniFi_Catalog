#!/usr/bin/env python3
"""Build deterministic catalog artifacts and the checked-in generated index."""

from __future__ import annotations

import argparse
from pathlib import Path

from catalog import CatalogError, build_index, canonical_json, catalog_sha256, normalized_catalog, validate_catalog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--check", action="store_true", help="check generated index without rewriting it")
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = (args.output_dir or root / "dist").resolve()
    try:
        models, _, _ = validate_catalog(root)
        index_bytes = canonical_json(build_index(models))
        index_path = root / "generated" / "catalog-index.json"
        if args.check:
            if not index_path.is_file() or index_path.read_bytes() != index_bytes:
                raise CatalogError("generated/catalog-index.json differs from the deterministic result")
        else:
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_bytes(index_bytes)
        catalog_bytes = canonical_json(normalized_catalog(models))
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "catalog.json").write_bytes(catalog_bytes)
        digest = catalog_sha256(catalog_bytes)
        (output_dir / "catalog.sha256").write_text(digest + "  catalog.json\n", encoding="utf-8")
        manifest = {"catalog_schema_version": 1, "model_count": len(models), "bundle_sha256": digest}
        (output_dir / "manifest.json").write_bytes(canonical_json(manifest))
    except CatalogError as exc:
        print(f"DETERMINISTIC_BUILD=FAIL: {exc}")
        return 1
    print(f"DETERMINISTIC_BUILD=PASS model_count={len(models)} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
