"""Exact-match reference resolver for future catalog consumers."""

from __future__ import annotations

from typing import Any


IDENTIFIER_PRIORITY = ("sysid", "api_model", "ssh_model")


def resolve_model(models: list[dict[str, Any]], value: str, *, identifier_type: str | None = None, explicit_sku: bool = False) -> dict[str, Any] | None:
    """Resolve only verified aliases, or a canonical SKU when explicitly requested."""
    if not isinstance(value, str) or not value:
        return None
    types = (identifier_type,) if identifier_type else IDENTIFIER_PRIORITY
    for current_type in types:
        for model in models:
            for alias in model["runtime_identifiers"].get(current_type, []):
                if alias["status"] == "verified" and alias["value"] == value:
                    return model
    if explicit_sku:
        for model in models:
            if model["canonical_sku"] == value:
                return model
    return None
