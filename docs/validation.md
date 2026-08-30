# Validation and release procedure

From the repository root:

```text
python3 -m pip install -r requirements-dev.txt
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


Semantic checks include the distinction between fixed, auto-detected and
controller-manual power profiles; field-level `unknown` values; absolute versus
profile PoE budgets; non-PoE zero-capability constraints; and exclusion of
unsupported profiles from automatic activation.

The validator performs real Draft 2020-12 JSON Schema validation for every
model and evidence instance and, when present, the generated index and bundle.
Python semantic validation then owns cross-file references, runtime SKU/value
binding, duplicate aliases, power consistency, qualification logic and
deterministic normalization. The same fail-closed Python secret scanner is
used by local validation and CI.
