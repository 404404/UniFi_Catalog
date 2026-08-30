# Validation and release procedure

From the repository root:

```text
python3 tools/validate_catalog.py
python3 tools/build_catalog.py
python3 tools/validate_catalog.py --check-generated
python3 -m unittest discover -s tests -v
python3 tools/build_catalog.py --check --output-dir /tmp/unifi-catalog-build-one
python3 tools/build_catalog.py --check --output-dir /tmp/unifi-catalog-build-two
```

The first build regenerates the checked-in index and writes ignored `dist/`
artifacts. CI builds into two clean temporary directories and compares the
resulting `catalog.json` bytes and SHA256. A Phase 1 release is a pinned
source revision plus the deterministic bundle SHA256; there is no package or
runtime GitHub fetch.
