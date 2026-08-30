#!/usr/bin/env python3
"""Draft 2020-12 validation for catalog instances."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker, RefResolver
except Exception as exc:
    Draft202012Validator = None
    FormatChecker = None
    RefResolver = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


class SchemaValidationError(ValueError):
    """Raised when schema validation cannot complete or an instance is invalid."""


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SchemaValidationError(f"invalid JSON: {path}: {exc}") from exc


def _validate(instance: Any, schema: dict[str, Any], name: str, store: dict[str, Any]) -> None:
    if Draft202012Validator is None:
        raise SchemaValidationError(f"Draft 2020-12 validator unavailable: {_IMPORT_ERROR}")
    try:
        Draft202012Validator.check_schema(schema)
        resolver = RefResolver(schema["$id"], schema, store=store)
        validator = Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    except Exception as exc:
        if isinstance(exc, SchemaValidationError):
            raise
        raise SchemaValidationError(f"schema validation could not execute for {name}: {exc}") from exc
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise SchemaValidationError(f"{name}: {location}: {error.message}")


def validate_json_schemas(root: Path) -> None:
    root = Path(root)
    schema_dir = root / "schema"
    schema_paths = sorted(schema_dir.glob("*.json"))
    if not schema_paths:
        raise SchemaValidationError("no checked-in JSON Schemas found")
    schemas = {path.name: _read(path) for path in schema_paths}
    for name, schema in schemas.items():
        if not isinstance(schema, dict) or "$id" not in schema:
            raise SchemaValidationError(f"{name}: schema must be an object with $id")
    store = {schema["$id"]: schema for schema in schemas.values()}
    if Draft202012Validator is None:
        raise SchemaValidationError(f"Draft 2020-12 validator unavailable: {_IMPORT_ERROR}")
    for path in schema_paths:
        try:
            Draft202012Validator.check_schema(schemas[path.name])
        except Exception as exc:
            raise SchemaValidationError(f"invalid JSON Schema {path}: {exc}") from exc

    model_schema = schemas["model.schema.json"]
    evidence_schema = schemas["evidence.schema.json"]
    catalog_schema = schemas["catalog.schema.json"]
    index_schema = schemas["index.schema.json"]

    for path in sorted((root / "models").glob("*.json")):
        _validate(_read(path), model_schema, str(path.relative_to(root)), store)
    for directory in ("official", "runtime"):
        for path in sorted((root / "evidence" / directory).glob("*.json")):
            _validate(_read(path), evidence_schema, str(path.relative_to(root)), store)

    generated_index = root / "generated" / "catalog-index.json"
    if generated_index.is_file():
        _validate(_read(generated_index), index_schema, str(generated_index.relative_to(root)), store)

    bundle = root / "dist" / "catalog.json"
    if bundle.is_file():
        _validate(_read(bundle), catalog_schema, str(bundle.relative_to(root)), store)


def validate_json_file(root: Path, path: Path, schema_name: str) -> None:
    root = Path(root)
    schema_paths = sorted((root / "schema").glob("*.json"))
    schemas = {item.name: _read(item) for item in schema_paths}
    if schema_name not in schemas:
        raise SchemaValidationError(f"missing schema: {schema_name}")
    if Draft202012Validator is None:
        raise SchemaValidationError(f"Draft 2020-12 validator unavailable: {_IMPORT_ERROR}")
    store = {schema["$id"]: schema for schema in schemas.values()}
    _validate(_read(Path(path)), schemas[schema_name], str(path), store)
