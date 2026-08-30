from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.catalog import (
    CatalogError,
    canonical_json,
    classify_poe_output,
    classify_storage,
    load_evidence,
    normalized_catalog,
    validate_catalog,
    validate_model,
)
from tools.model_resolver import resolve_model


ROOT = Path(__file__).resolve().parents[1]


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.models, self.official, self.runtime = validate_catalog(ROOT)

    def model(self, filename: str) -> dict:
        return copy.deepcopy(next(model for model in self.models if model["canonical_sku"].lower() + ".json" == filename))

    def fixture_runtime(self) -> dict:
        fixture = json.loads((ROOT / "fixtures" / "runtime-identity-cases.json").read_text(encoding="utf-8"))
        evidence = fixture["qualified_evidence"]
        return {evidence["id"]: evidence}

    def add_alias(self, model: dict, identifier_type: str, value: str, status: str = "verified") -> None:
        model["runtime_identifiers"][identifier_type].append({
            "value": value,
            "status": status,
            "provenance": "synthetic_fixture",
            "evidence_id": "runtime-fixture-qualified",
        })

    def test_first_batch_has_fifteen_canonical_models(self):
        self.assertEqual(len(self.models), 15)
        self.assertEqual(
            [model["canonical_sku"] for model in self.models],
            sorted((model["canonical_sku"] for model in self.models), key=str.lower),
        )

    def test_verified_alias_resolves_exactly(self):
        model = self.model("ucg-max.json")
        self.add_alias(model, "sysid", "fixture-sysid")
        self.add_alias(model, "api_model", "Fixture API")
        self.assertIs(resolve_model([model], "fixture-sysid", identifier_type="sysid"), model)
        self.assertIs(resolve_model([model], "Fixture API", identifier_type="api_model"), model)

    def test_candidate_alias_does_not_resolve(self):
        model = self.model("ucg-max.json")
        self.add_alias(model, "ssh_model", "Fixture SSH Candidate", status="candidate")
        self.assertIsNone(resolve_model([model], "Fixture SSH Candidate"))

    def test_display_name_does_not_resolve(self):
        model = self.model("ucg-max.json")
        self.assertIsNone(resolve_model([model], model["display_name"]))

    def test_canonical_sku_requires_explicit_flag(self):
        model = self.model("ucg-max.json")
        self.assertIsNone(resolve_model([model], "UCG-Max"))
        self.assertIs(resolve_model([model], "UCG-Max", explicit_sku=True), model)

    def test_duplicate_verified_alias_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary) / "catalog"
            shutil.copytree(ROOT, temporary_root)
            runtime_path = temporary_root / "evidence" / "runtime" / "fixture.json"
            runtime_path.write_text(json.dumps(next(iter(self.fixture_runtime().values())), indent=2) + "\n", encoding="utf-8")
            for filename in ("ucg-max.json", "udw.json"):
                path = temporary_root / "models" / filename
                model = json.loads(path.read_text(encoding="utf-8"))
                self.add_alias(model, "sysid", "same-verified-sysid")
                path.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(CatalogError, "duplicate verified runtime alias"):
                validate_catalog(temporary_root)

    def test_duplicate_port_index_fails(self):
        model = self.model("usw-flex-mini.json")
        model["ports"]["items"][1]["index"] = 1
        with self.assertRaisesRegex(CatalogError, "duplicate physical port index"):
            validate_model(model, self.official, self.runtime)

    def test_invalid_combo_group_fails(self):
        model = self.model("usw-flex-mini.json")
        model["ports"]["items"][0]["combo_group"] = "uplink"
        with self.assertRaisesRegex(CatalogError, "combo group"):
            validate_model(model, self.official, self.runtime)

    def test_complete_no_poe_is_distinct_from_unknown(self):
        ucg = self.model("ucg-max.json")
        self.assertEqual(classify_poe_output(ucg), "none")
        incomplete = copy.deepcopy(ucg)
        incomplete["ports"]["complete"] = False
        self.assertEqual(classify_poe_output(incomplete), "unknown")

    def test_max_speed_is_static_model_data(self):
        model = self.model("usw-flex-2.5g-5.json")
        self.assertEqual({port["max_speed_mbps"] for port in model["ports"]["items"]}, {2500})
        self.assertFalse(any("negotiated_speed_mbps" in port for port in model["ports"]["items"]))

    def test_storage_completeness_semantics(self):
        model = self.model("ucg-max.json")
        model["storage"] = {"complete": True, "items": []}
        self.assertEqual(classify_storage(model), "none")
        incomplete = self.model("usw-flex-mini.json")
        self.assertEqual(classify_storage(incomplete), "unknown")

    def test_unknown_fan_is_not_present(self):
        for model in self.models:
            self.assertEqual(model["fans"], {"status": "unknown", "count": None})

    def test_deterministic_catalog_serialization(self):
        first = canonical_json(normalized_catalog(self.models))
        second = canonical_json(normalized_catalog(self.models))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
