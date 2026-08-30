"""Dependency-free catalog contracts, validation and deterministic serialization."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any


class CatalogError(ValueError):
    """Raised when a catalog contract or evidence rule is violated."""


MODEL_REQUIRED = {
    "schema_version",
    "canonical_sku",
    "display_name",
    "device_type",
    "official_evidence_ids",
    "runtime_identifiers",
    "ports",
    "storage",
    "power",
    "fans",
}
MODEL_OPTIONAL = {"processor"}
IDENTIFIER_TYPES = ("api_model", "sysid", "ssh_model")
CONNECTORS = {"rj45", "sfp", "sfp_plus", "sfp28", "other"}
ROLES = {"lan", "wan"}
SPEEDS = {10, 100, 1000, 2500, 5000, 10000, 25000, 100000}
POE_STANDARDS = {"poe", "poe+", "poe++", "poe+++"}
STORAGE_TYPES = {"emmc", "ssd", "sata_ssd", "nvme", "microsd", "tf", "other"}
STORAGE_KINDS = {"fixed_device", "user_slot", "removable_media"}
PRESENCE = {"present", "not_populated", "unknown"}
POWER_SOURCES = {
    "integrated_ac",
    "integrated_ac_with_dc_backup",
    "external_adapter",
    "external_adapter_or_poe",
    "poe_powered",
    "dc_or_external_adapter",
    "unknown",
}
POWER_PROFILE_STATUSES = {"verified", "candidate", "unsupported"}
SELECTION_MODES = {"fixed", "auto_detected", "controller_manual"}
INPUT_METHODS = {"ac_mains", "ac_adapter", "dc_adapter", "usb_c", "poe"}
POWER_FIELD_STATUSES = {"verified", "candidate", "unknown", "not_applicable"}
POWER_PROFILE_FIELDS = ("selection_mode", "input_method", "input_poe_class", "input_capacity_w", "poe_budget_w")
FAN_STATUS = {"present", "absent", "unknown"}
RUNTIME_KINDS = {"qualified_controller", "qualified_ssh"}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)authorization\s*[:=]"),
    re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|session[_-]?cookie|password)\s*[:=]"),
    re.compile(r"(?i)\b(?:ssh_password|controller_token|private_key)\b"),
    re.compile(r"(?i)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b"),
)


def canonical_filename(canonical_sku: str) -> str:
    return canonical_sku.lower() + ".json"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CatalogError(message)


def _object(value: Any, name: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{name}: expected object")
    return value


def _keys(value: dict[str, Any], required: set[str], optional: set[str], name: str) -> None:
    _require(required <= set(value), f"{name}: missing {sorted(required - set(value))}")
    _require(not (set(value) - required - optional), f"{name}: unexpected {sorted(set(value) - required - optional)}")


def _number(value: Any, name: str, *, nullable: bool = True) -> None:
    if value is None and nullable:
        return
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{name}: invalid number")
    _require(value >= 0, f"{name}: negative number")


def validate_official_evidence(evidence: dict[str, Any]) -> None:
    _keys(evidence, {"id", "kind", "canonical_sku", "sources", "fields_supported", "notes"}, set(), "official evidence")
    _require(isinstance(evidence["id"], str) and evidence["id"].startswith("official-"), "official evidence: invalid id")
    _require(evidence["kind"] == "official_spec", "official evidence: invalid kind")
    _require(isinstance(evidence["canonical_sku"], str), "official evidence: invalid canonical_sku")
    _require(isinstance(evidence["sources"], list) and evidence["sources"], "official evidence: sources required")
    for index, source in enumerate(evidence["sources"]):
        _keys(source, {"url", "publisher", "title", "retrieved_on", "evidence_note"}, set(), f"official source {index}")
        _require(isinstance(source["url"], str) and source["url"].startswith("https://"), f"official source {index}: URL must be HTTPS")
        _require(source["publisher"] == "Ubiquiti", f"official source {index}: publisher must be Ubiquiti")
        _require(isinstance(source["retrieved_on"], str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["retrieved_on"]), f"official source {index}: invalid date")
    _require(isinstance(evidence["fields_supported"], list) and evidence["fields_supported"], "official evidence: fields_supported required")
    _require(isinstance(evidence["notes"], str) and evidence["notes"].strip(), "official evidence: notes required")


def validate_runtime_evidence(evidence: dict[str, Any]) -> None:
    _keys(evidence, {"id", "kind", "supports", "observed_on"}, {"source_note"}, "runtime evidence")
    _require(isinstance(evidence["id"], str) and evidence["id"].startswith("runtime-"), "runtime evidence: invalid id")
    _require(evidence["kind"] in RUNTIME_KINDS, "runtime evidence: invalid kind")
    supports = _object(evidence["supports"], "runtime evidence.supports")
    _require(set(supports) <= set(IDENTIFIER_TYPES) and supports, "runtime evidence.supports: invalid fields")
    _require(all(isinstance(value, str) and value for value in supports.values()), "runtime evidence.supports: invalid value")
    _require(isinstance(evidence["observed_on"], str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", evidence["observed_on"]), "runtime evidence: invalid date")


def _validate_processor(processor: Any) -> None:
    processor = _object(processor, "processor")
    _keys(processor, {"model", "architecture", "cores", "clock_mhz"}, set(), "processor")
    _require(processor["model"] is None or isinstance(processor["model"], str), "processor.model: invalid value")
    _require(isinstance(processor["architecture"], str) and processor["architecture"].strip(), "processor.architecture: invalid value")
    if processor["cores"] is not None:
        _require(isinstance(processor["cores"], int) and processor["cores"] > 0, "processor.cores: invalid value")
    if processor["clock_mhz"] is not None:
        _require(isinstance(processor["clock_mhz"], int) and processor["clock_mhz"] > 0, "processor.clock_mhz: invalid value")


def _validate_ports(ports: Any) -> None:
    ports = _object(ports, "ports")
    _keys(ports, {"complete", "items"}, set(), "ports")
    _require(isinstance(ports["complete"], bool), "ports.complete: invalid value")
    _require(isinstance(ports["items"], list), "ports.items: expected array")
    indexes: set[int] = set()
    combo_members: dict[str, list[int]] = {}
    for item_number, port in enumerate(ports["items"]):
        name = f"ports.items[{item_number}]"
        port = _object(port, name)
        _keys(port, {"index", "label", "connector", "roles", "max_speed_mbps", "poe_in", "poe_out", "poe_standard", "poe_max_power_w", "combo_group"}, set(), name)
        _require(isinstance(port["index"], int) and port["index"] > 0, f"{name}.index: invalid value")
        _require(port["index"] not in indexes, f"duplicate physical port index: {port['index']}")
        indexes.add(port["index"])
        _require(isinstance(port["label"], str) and port["label"].strip(), f"{name}.label: invalid value")
        _require(port["connector"] in CONNECTORS, f"{name}.connector: invalid value")
        _require(isinstance(port["roles"], list) and port["roles"] and set(port["roles"]) <= ROLES, f"{name}.roles: invalid value")
        speed = port["max_speed_mbps"]
        _require(speed is None or (isinstance(speed, int) and speed in SPEEDS), f"{name}.max_speed_mbps: invalid value")
        for direction in ("poe_in", "poe_out"):
            _require(port[direction] is None or isinstance(port[direction], bool), f"{name}.{direction}: invalid value")
        standard = port["poe_standard"]
        _require(standard is None or standard in POE_STANDARDS, f"{name}.poe_standard: invalid value")
        _number(port["poe_max_power_w"], f"{name}.poe_max_power_w")
        if port["poe_out"] is False:
            _require(port["poe_max_power_w"] is None, f"{name}: non-output port cannot have output wattage")
        group = port["combo_group"]
        _require(group is None or (isinstance(group, str) and group.strip()), f"{name}.combo_group: invalid value")
        if group:
            combo_members.setdefault(group, []).append(port["index"])
    for group, members in combo_members.items():
        _require(len(members) >= 2, f"combo group {group!r} must have at least two members")


def classify_poe_output(model: dict[str, Any]) -> str:
    """Return present, none, or unknown without treating missing evidence as none."""
    outputs = [port["poe_out"] for port in model["ports"]["items"]]
    if any(value is True for value in outputs):
        return "present"
    if model["ports"]["complete"] and outputs and all(value is False for value in outputs):
        return "none"
    return "unknown"


def classify_storage(model: dict[str, Any]) -> str:
    """Return present-capability, none, or unknown from explicit completeness."""
    storage = model["storage"]
    if not storage["complete"]:
        return "unknown"
    return "none" if not storage["items"] else "present-capability"


def _validate_storage(storage: Any) -> None:
    storage = _object(storage, "storage")
    _keys(storage, {"complete", "items"}, set(), "storage")
    _require(isinstance(storage["complete"], bool), "storage.complete: invalid value")
    _require(isinstance(storage["items"], list), "storage.items: expected array")
    for item_number, item in enumerate(storage["items"]):
        name = f"storage.items[{item_number}]"
        item = _object(item, name)
        _keys(item, {"type", "kind", "default_presence", "capacity_bytes", "max_capacity_bytes"}, set(), name)
        _require(item["type"] in STORAGE_TYPES, f"{name}.type: invalid value")
        _require(item["kind"] in STORAGE_KINDS, f"{name}.kind: invalid value")
        _require(item["default_presence"] in PRESENCE, f"{name}.default_presence: invalid value")
        for field in ("capacity_bytes", "max_capacity_bytes"):
            value = item[field]
            _require(value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 0), f"{name}.{field}: invalid value")
        if item["capacity_bytes"] is not None and item["max_capacity_bytes"] is not None:
            _require(item["capacity_bytes"] <= item["max_capacity_bytes"], f"{name}: capacity exceeds maximum")


def _validate_power_field_evidence(value: Any, field_evidence: Any, name: str, evidence: dict[str, dict[str, Any]]) -> None:
    field_evidence = _object(field_evidence, name)
    _keys(field_evidence, {"status", "evidence_ids"}, {"source_note"}, name)
    status = field_evidence["status"]
    _require(status in POWER_FIELD_STATUSES, f"{name}.status: invalid value")
    evidence_ids = field_evidence["evidence_ids"]
    _require(isinstance(evidence_ids, list) and len(evidence_ids) == len(set(evidence_ids)), f"{name}.evidence_ids: invalid value")
    _require(all(isinstance(evidence_id, str) and evidence_id in evidence for evidence_id in evidence_ids), f"{name}.evidence_ids: unknown evidence reference")
    source_note = field_evidence.get("source_note")
    _require(source_note is None or (isinstance(source_note, str) and source_note.strip()), f"{name}.source_note: invalid value")
    _require(evidence_ids or source_note, f"{name}: evidence_ids or source_note required")
    if status in {"unknown", "not_applicable"}:
        _require(value is None, f"{name}: {status} field must be null")
    elif value is None:
        _require(False, f"{name}: {status} field must not be null")


def _validate_power(power: Any, evidence: dict[str, dict[str, Any]], *, poe_output_state: str) -> None:
    power = _object(power, "power")
    _keys(power, {"source_type", "psu_slots", "max_power_w", "absolute_max_poe_budget_w", "power_profiles"}, set(), "power")
    _require(power["source_type"] in POWER_SOURCES, "power.source_type: invalid value")
    slots = power["psu_slots"]
    _require(slots is None or (isinstance(slots, int) and not isinstance(slots, bool) and slots >= 0), "power.psu_slots: invalid value")
    _number(power["max_power_w"], "power.max_power_w")
    absolute = power["absolute_max_poe_budget_w"]
    _number(absolute, "power.absolute_max_poe_budget_w")
    profiles = power["power_profiles"]
    _require(isinstance(profiles, list) and profiles, "power.power_profiles: at least one profile required")
    profile_ids: set[str] = set()
    for profile_number, profile in enumerate(profiles):
        name = f"power.power_profiles[{profile_number}]"
        profile = _object(profile, name)
        _keys(profile, {"id", "status", "selection_mode", "input_method", "input_poe_class", "input_capacity_w", "poe_budget_w", "field_evidence"}, set(), name)
        profile_id = profile["id"]
        _require(isinstance(profile_id, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]*", profile_id), f"{name}.id: invalid value")
        _require(profile_id not in profile_ids, f"duplicate power profile id: {profile_id}")
        profile_ids.add(profile_id)
        _require(profile["status"] in POWER_PROFILE_STATUSES, f"{name}.status: invalid value")
        selection_mode = profile["selection_mode"]
        input_method = profile["input_method"]
        input_poe_class = profile["input_poe_class"]
        _require(selection_mode in SELECTION_MODES, f"{name}.selection_mode: invalid value")
        _require(input_method in INPUT_METHODS, f"{name}.input_method: invalid value")
        _require(input_poe_class is None or input_poe_class in POE_STANDARDS, f"{name}.input_poe_class: invalid value")
        _number(profile["input_capacity_w"], f"{name}.input_capacity_w")
        _number(profile["poe_budget_w"], f"{name}.poe_budget_w")
        if selection_mode == "auto_detected":
            _require(input_method == "poe", f"{name}: auto_detected profiles must use PoE input")
        if selection_mode == "controller_manual":
            _require(input_method == "dc_adapter", f"{name}: controller_manual profiles must use dc_adapter input")
        if selection_mode == "fixed":
            _require(input_method != "poe", f"{name}: fixed profiles cannot use negotiated PoE input")
        if input_method == "poe":
            _require(selection_mode == "auto_detected", f"{name}: PoE input must be auto_detected")
        else:
            _require(input_poe_class is None, f"{name}: non-PoE input cannot declare an input PoE class")
        field_evidence = _object(profile["field_evidence"], f"{name}.field_evidence")
        _keys(field_evidence, set(POWER_PROFILE_FIELDS), set(), f"{name}.field_evidence")
        for field in POWER_PROFILE_FIELDS:
            _validate_power_field_evidence(profile[field], field_evidence[field], f"{name}.field_evidence.{field}", evidence)
        if poe_output_state == "none":
            _require(absolute in {0, None}, "power.absolute_max_poe_budget_w: non-PoE model cannot have a positive budget")
            _require(profile["poe_budget_w"] in {0, None}, f"{name}.poe_budget_w: non-PoE model cannot have a positive budget")
        if absolute is not None and profile["poe_budget_w"] is not None:
            _require(profile["poe_budget_w"] <= absolute, f"{name}.poe_budget_w exceeds power.absolute_max_poe_budget_w")


def active_power_profiles(model: dict[str, Any], *, selection_mode: str | None = None) -> list[dict[str, Any]]:
    """Return only qualified profiles; unsupported and candidate profiles are never active."""
    profiles = [profile for profile in model["power"]["power_profiles"] if profile["status"] == "verified"]
    if selection_mode is not None:
        profiles = [profile for profile in profiles if profile["selection_mode"] == selection_mode]
    return profiles


def power_profile_budget(profile: dict[str, Any]) -> float | int | None:
    """Preserve null as unknown; never coerce an unknown budget to zero."""
    return profile["poe_budget_w"]


def _validate_fans(fans: Any) -> None:
    fans = _object(fans, "fans")
    _keys(fans, {"status", "count"}, set(), "fans")
    _require(fans["status"] in FAN_STATUS, "fans.status: invalid value")
    count = fans["count"]
    _require(count is None or (isinstance(count, int) and not isinstance(count, bool) and count >= 0), "fans.count: invalid value")
    if fans["status"] == "present":
        _require(count is not None and count > 0, "present fans require a positive count")
    if fans["status"] == "absent":
        _require(count == 0, "absent fans require count=0")
    if fans["status"] == "unknown":
        _require(count is None, "unknown fans require count=null")


def _validate_runtime_identifiers(value: Any, runtime_evidence: dict[str, dict[str, Any]]) -> list[tuple[str, str, str]]:
    identifiers = _object(value, "runtime_identifiers")
    _keys(identifiers, set(IDENTIFIER_TYPES), set(), "runtime_identifiers")
    seen: list[tuple[str, str, str]] = []
    for identifier_type in IDENTIFIER_TYPES:
        aliases = identifiers[identifier_type]
        _require(isinstance(aliases, list), f"runtime_identifiers.{identifier_type}: expected array")
        local_values: set[str] = set()
        for alias_number, alias in enumerate(aliases):
            name = f"runtime_identifiers.{identifier_type}[{alias_number}]"
            alias = _object(alias, name)
            _keys(alias, {"value", "status", "provenance", "evidence_id"}, set(), name)
            _require(isinstance(alias["value"], str) and alias["value"], f"{name}.value: invalid value")
            _require(alias["value"] not in local_values, f"duplicate runtime alias in {identifier_type}: {alias['value']}")
            local_values.add(alias["value"])
            _require(alias["status"] in {"candidate", "verified"}, f"{name}.status: invalid value")
            _require(isinstance(alias["provenance"], str) and alias["provenance"].strip(), f"{name}.provenance: invalid value")
            evidence_id = alias["evidence_id"]
            _require(evidence_id in runtime_evidence, f"{name}: evidence reference does not exist: {evidence_id}")
            if alias["status"] == "verified":
                _require(runtime_evidence[evidence_id]["kind"] in RUNTIME_KINDS, f"{name}: verified alias lacks qualified runtime evidence")
            seen.append((identifier_type, alias["value"], evidence_id))
    return seen


def validate_model(model: dict[str, Any], official_evidence: dict[str, dict[str, Any]], runtime_evidence: dict[str, dict[str, Any]], *, filename: str | None = None) -> list[tuple[str, str, str]]:
    _keys(model, MODEL_REQUIRED, MODEL_OPTIONAL, "model")
    _require(model["schema_version"] == 1, "model.schema_version: unsupported")
    sku = model["canonical_sku"]
    _require(isinstance(sku, str) and re.fullmatch(r"[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*", sku), "model.canonical_sku: invalid value")
    if filename is not None:
        _require(filename == canonical_filename(sku), f"canonical SKU filename mismatch: {filename} != {canonical_filename(sku)}")
    _require(isinstance(model["display_name"], str) and model["display_name"].strip(), "model.display_name: invalid value")
    _require(model["device_type"] in {"gateway", "switch", "ap"}, "model.device_type: invalid value")
    if "processor" in model:
        _validate_processor(model["processor"])
    official_ids = model["official_evidence_ids"]
    _require(isinstance(official_ids, list) and official_ids, "model.official_evidence_ids: required")
    for evidence_id in official_ids:
        _require(evidence_id in official_evidence, f"model: official evidence reference does not exist: {evidence_id}")
        _require(official_evidence[evidence_id]["canonical_sku"] == sku, f"model: official evidence SKU mismatch: {evidence_id}")
    runtime_aliases = _validate_runtime_identifiers(model["runtime_identifiers"], runtime_evidence)
    _validate_ports(model["ports"])
    _validate_storage(model["storage"])
    output_values = [port["poe_out"] for port in model["ports"]["items"]]
    poe_output_state = "present" if any(value is True for value in output_values) else "none" if model["ports"]["complete"] and output_values and all(value is False for value in output_values) else "unknown"
    _validate_power(model["power"], {**official_evidence, **runtime_evidence}, poe_output_state=poe_output_state)
    _validate_fans(model["fans"])
    return runtime_aliases


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"invalid JSON: {path}: {exc}") from exc
    return _object(value, str(path))


def load_evidence(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    official: dict[str, dict[str, Any]] = {}
    runtime: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "evidence" / "official").glob("*.json")):
        evidence = _load_json(path)
        validate_official_evidence(evidence)
        _require(evidence["id"] not in official, f"duplicate official evidence id: {evidence['id']}")
        official[evidence["id"]] = evidence
    for path in sorted((root / "evidence" / "runtime").glob("*.json")):
        evidence = _load_json(path)
        validate_runtime_evidence(evidence)
        _require(evidence["id"] not in runtime, f"duplicate runtime evidence id: {evidence['id']}")
        runtime[evidence["id"]] = evidence
    return official, runtime


def load_models(root: Path) -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    for path in sorted((root / "models").glob("*.json")):
        model = _load_json(path)
        model["__filename"] = path.name
        models.append(model)
    return models


def _secret_scan(value: Any, name: str) -> None:
    serialized = json.dumps(value, ensure_ascii=False)
    for pattern in SECRET_PATTERNS:
        _require(not pattern.search(serialized), f"secret-like pattern found in {name}: {pattern.pattern}")


def validate_catalog(root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    root = Path(root)
    for schema_path in sorted((root / "schema").glob("*.json")):
        _load_json(schema_path)
    official, runtime = load_evidence(root)
    models = load_models(root)
    _require(models, "catalog contains no models")
    skus: set[str] = set()
    verified_aliases: dict[tuple[str, str], str] = {}
    for model in models:
        filename = model.pop("__filename")
        validate_model(model, official, runtime, filename=filename)
        _secret_scan(model, f"models/{filename}")
        sku = model["canonical_sku"]
        _require(sku not in skus, f"duplicate canonical SKU: {sku}")
        skus.add(sku)
        for identifier_type, value, _ in _validate_runtime_identifiers(model["runtime_identifiers"], runtime):
            alias = next(alias for alias in model["runtime_identifiers"][identifier_type] if alias["value"] == value)
            if alias["status"] == "verified":
                owner_key = (identifier_type, value)
                _require(owner_key not in verified_aliases, f"duplicate verified runtime alias: {identifier_type}={value!r} ({verified_aliases.get(owner_key)})")
                verified_aliases[owner_key] = sku
    for evidence_id, evidence in {**official, **runtime}.items():
        _secret_scan(evidence, f"evidence/{evidence_id}")
    models.sort(key=lambda model: model["canonical_sku"].lower())
    _require([model["canonical_sku"] for model in models] == sorted(skus, key=str.lower), "model files must be in deterministic canonical SKU order")
    return models, official, runtime


def normalized_model(model: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(model)
    result["official_evidence_ids"] = sorted(result["official_evidence_ids"])
    for identifier_type in IDENTIFIER_TYPES:
        result["runtime_identifiers"][identifier_type] = sorted(
            result["runtime_identifiers"][identifier_type],
            key=lambda alias: (alias["value"], alias["status"], alias["provenance"], alias["evidence_id"]),
        )
    result["ports"]["items"] = sorted(result["ports"]["items"], key=lambda port: port["index"])
    result["storage"]["items"] = sorted(
        result["storage"]["items"],
        key=lambda item: (item["type"], item["kind"], item["default_presence"], item["capacity_bytes"] is None, item["capacity_bytes"] or 0),
    )
    result["power"]["power_profiles"] = sorted(result["power"]["power_profiles"], key=lambda profile: profile["id"])
    return result


def normalized_catalog(models: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "models": [normalized_model(model) for model in sorted(models, key=lambda model: model["canonical_sku"].lower())],
    }


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, separators=(",", ": ")) + "\n").encode("utf-8")


def build_index(models: list[dict[str, Any]]) -> dict[str, Any]:
    index_models = []
    for model in sorted(models, key=lambda item: item["canonical_sku"].lower()):
        verified = {
            identifier_type: sorted(alias["value"] for alias in model["runtime_identifiers"][identifier_type] if alias["status"] == "verified")
            for identifier_type in IDENTIFIER_TYPES
        }
        index_models.append({
            "canonical_sku": model["canonical_sku"],
            "display_name": model["display_name"],
            "device_type": model["device_type"],
            "source_file": "models/" + canonical_filename(model["canonical_sku"]),
            "port_count": len(model["ports"]["items"]),
            "ports_complete": model["ports"]["complete"],
            "storage_complete": model["storage"]["complete"],
            "fan_status": model["fans"]["status"],
            "absolute_max_poe_budget_w": model["power"]["absolute_max_poe_budget_w"],
            "power_profile_count": len(model["power"]["power_profiles"]),
            "verified_power_profile_ids": sorted(profile["id"] for profile in model["power"]["power_profiles"] if profile["status"] == "verified"),
            "verified_runtime_identifiers": verified,
        })
    return {"schema_version": 1, "model_count": len(index_models), "models": index_models}


def catalog_sha256(catalog_bytes: bytes) -> str:
    return hashlib.sha256(catalog_bytes).hexdigest()


def check_generated_index(root: Path, models: list[dict[str, Any]]) -> None:
    path = Path(root) / "generated" / "catalog-index.json"
    expected = canonical_json(build_index(models))
    _require(path.is_file(), "generated/catalog-index.json is missing; run tools/build_catalog.py")
    _require(path.read_bytes() == expected, "generated/catalog-index.json is stale; regenerate it")
