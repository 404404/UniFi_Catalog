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
    active_power_profiles,
    classify_poe_output,
    classify_storage,
    load_evidence,
    normalized_catalog,
    power_profile_budget,
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

    def test_catalog_has_twenty_canonical_models(self):
        self.assertEqual(len(self.models), 20)
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

    def test_flex_25g_poe_manual_profiles_are_field_qualified(self):
        model = self.model("usw-flex-2.5g-8-poe.json")
        profiles = {profile["id"]: profile for profile in model["power"]["power_profiles"]}
        for profile_id, capacity in (("dc-60w", 60), ("dc-210w", 210)):
            profile = profiles[profile_id]
            self.assertEqual(profile["status"], "verified")
            self.assertEqual(profile["selection_mode"], "controller_manual")
            self.assertEqual(profile["input_method"], "dc_adapter")
            self.assertEqual(profile["input_capacity_w"], capacity)
            self.assertIsNone(profile["poe_budget_w"])
            self.assertEqual(profile["field_evidence"]["poe_budget_w"]["status"], "unknown")
            self.assertIsNone(power_profile_budget(profile))

    def test_power_profile_semantics_and_absolute_budget(self):
        model = self.model("usw-flex-2.5g-8-poe.json")
        profiles = model["power"]["power_profiles"]
        self.assertGreaterEqual(len(profiles), 2)
        self.assertEqual(model["power"]["absolute_max_poe_budget_w"], 196)
        for profile in profiles:
            if profile["poe_budget_w"] is not None:
                self.assertLessEqual(profile["poe_budget_w"], model["power"]["absolute_max_poe_budget_w"])
        self.assertTrue(any(profile["selection_mode"] == "auto_detected" for profile in profiles))
        self.assertTrue(any(profile["selection_mode"] == "controller_manual" for profile in profiles))

    def test_fixed_ac_power_profile_is_explicit(self):
        model = self.model("usw-pro-max-24.json")
        profile = next(profile for profile in model["power"]["power_profiles"] if profile["id"] == "ac-mains")
        self.assertEqual(profile["status"], "verified")
        self.assertEqual(profile["selection_mode"], "fixed")
        self.assertEqual(profile["input_method"], "ac_mains")
        self.assertEqual(profile["input_capacity_w"], 60)
        self.assertIsNone(profile["input_poe_class"])

    def test_known_profile_budget_cannot_exceed_absolute_budget(self):
        model = self.model("usw-flex-2.5g-8-poe.json")
        model["power"]["absolute_max_poe_budget_w"] = 75
        with self.assertRaisesRegex(CatalogError, "exceeds power.absolute_max_poe_budget_w"):
            validate_model(model, self.official, self.runtime)

    def test_unsupported_profile_is_not_active_automatically(self):
        model = self.model("usw-flex-2.5g-8-poe.json")
        unsupported = copy.deepcopy(model["power"]["power_profiles"][0])
        unsupported["id"] = "unsupported-example"
        unsupported["status"] = "unsupported"
        model["power"]["power_profiles"].append(unsupported)
        self.assertNotIn("unsupported-example", [profile["id"] for profile in active_power_profiles(model)])

    def test_non_poe_models_reject_positive_output_budget(self):
        for filename in ("usw-pro-hd-24.json", "usw-pro-max-16.json", "usw-pro-max-24.json", "usw-flex-2.5g-8.json"):
            model = self.model(filename)
            self.assertEqual(classify_poe_output(model), "none")
            self.assertEqual(model["power"]["absolute_max_poe_budget_w"], 0)
            self.assertTrue(all(profile["poe_budget_w"] is None for profile in model["power"]["power_profiles"]))
            invalid = copy.deepcopy(model)
            invalid["power"]["absolute_max_poe_budget_w"] = 1
            with self.assertRaisesRegex(CatalogError, "non-PoE model cannot have a positive budget"):
                validate_model(invalid, self.official, self.runtime)
            invalid_profile = copy.deepcopy(model)
            invalid_profile["power"]["power_profiles"][0]["poe_budget_w"] = 1
            invalid_profile["power"]["power_profiles"][0]["field_evidence"]["poe_budget_w"] = {
                "status": "verified", "evidence_ids": [invalid_profile["official_evidence_ids"][0]]
            }
            with self.assertRaisesRegex(CatalogError, "non-PoE model cannot have a positive budget"):
                validate_model(invalid_profile, self.official, self.runtime)

    def test_sibling_models_are_independent(self):
        sibling_pairs = (
            ("usw-pro-hd-24.json", "usw-pro-hd-24-poe.json"),
            ("usw-pro-max-16.json", "usw-pro-max-16-poe.json"),
            ("usw-pro-max-24.json", "usw-pro-max-24-poe.json"),
            ("usw-flex-2.5g-8.json", "usw-flex-2.5g-8-poe.json"),
        )
        for standard_filename, poe_filename in sibling_pairs:
            standard = self.model(standard_filename)
            poe = self.model(poe_filename)
            self.assertNotEqual(standard["canonical_sku"], poe["canonical_sku"])
            self.assertNotEqual(standard["ports"], poe["ports"])
            self.assertNotEqual(standard["power"], poe["power"])
            self.assertEqual(classify_poe_output(standard), "none")
            self.assertEqual(standard["power"]["absolute_max_poe_budget_w"], 0)
            self.assertTrue(all(port["combo_group"] is None for port in standard["ports"]["items"]))
            self.assertTrue(any(port["poe_out"] is True for port in poe["ports"]["items"]))

    def test_sibling_runtime_aliases_remain_sku_specific(self):
        standard = self.model("usw-pro-max-16.json")
        poe = self.model("usw-pro-max-16-poe.json")
        self.add_alias(standard, "sysid", "sibling-specific-sysid")
        self.assertIs(resolve_model([standard, poe], "sibling-specific-sysid", identifier_type="sysid"), standard)
        self.assertIsNone(resolve_model([poe], "sibling-specific-sysid", identifier_type="sysid"))

    def test_deterministic_catalog_serialization(self):
        first = canonical_json(normalized_catalog(self.models))
        second = canonical_json(normalized_catalog(self.models))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
