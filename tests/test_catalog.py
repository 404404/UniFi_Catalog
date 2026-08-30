from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
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
        self.runtime.update(self.fixture_runtime())

    def model(self, filename: str) -> dict:
        return copy.deepcopy(next(model for model in self.models if model["canonical_sku"].lower() + ".json" == filename))

    def fixture_runtime(self) -> dict:
        fixture = json.loads((ROOT / "fixtures" / "runtime-identity-cases.json").read_text(encoding="utf-8"))
        evidence = fixture["qualified_evidence"]
        return {evidence["id"]: evidence}

    def add_alias(self, model: dict, identifier_type: str, value: str, status: str = "verified", evidence_id: str = "runtime-fixture-qualified") -> None:
        model["runtime_identifiers"][identifier_type].append({
            "value": value,
            "status": status,
            "provenance": "synthetic_fixture",
            "evidence_id": evidence_id,
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
            for filename, sku in (("ucg-max.json", "UCG-Max"), ("udw.json", "UDW")):
                evidence = next(iter(self.fixture_runtime().values())).copy()
                evidence["id"] = "runtime-fixture-" + sku.lower()
                evidence["canonical_sku"] = sku
                evidence["supports"] = {"sysid": "same-verified-sysid"}
                runtime_path = temporary_root / "evidence" / "runtime" / (evidence["id"] + ".json")
                runtime_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
                path = temporary_root / "models" / filename
                model = json.loads(path.read_text(encoding="utf-8"))
                self.add_alias(model, "sysid", "same-verified-sysid", evidence_id=evidence["id"])
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

    def test_udw_and_ucg_static_soc_evidence_is_bound(self):
        for filename, evidence_id, soc in (
            ("udw.json", "runtime-static-udw-processor-model-20260830", "Annapurna AL324"),
            ("ucg-max.json", "runtime-static-ucg-max-processor-model-20260830", "Qualcomm IPQ5322"),
        ):
            model = self.model(filename)
            evidence = self.runtime[evidence_id]
            self.assertEqual(model["processor"]["model"], soc)
            self.assertEqual(evidence["canonical_sku"], model["canonical_sku"])
            self.assertEqual(evidence["field_path"], "processor.model")
            self.assertEqual(evidence["observed_value"], soc)
            self.assertEqual(evidence["qualification_state"], "verified")
            self.assertNotIn("supports", evidence)

    def test_udw_power_quantities_remain_distinct(self):
        power = self.model("udw.json")["power"]
        self.assertEqual(power["psu_slots"], 2)
        self.assertEqual(power["psu_unit_capacity_w"], 550)
        self.assertEqual(power["controller_reference_capacity_w"], 550)
        self.assertEqual(power["max_device_consumption_w"], 532)
        self.assertEqual(power["absolute_max_poe_budget_w"], 420)
        self.assertNotIn("max_power_w", power)

    def test_cross_sku_runtime_evidence_fails(self):
        model = self.model("udw.json")
        self.add_alias(model, "sysid", "fixture-sysid")
        with self.assertRaisesRegex(CatalogError, "runtime evidence SKU mismatch"):
            validate_model(model, self.official, self.runtime)

    def test_runtime_alias_value_must_match_evidence(self):
        model = self.model("ucg-max.json")
        self.add_alias(model, "sysid", "wrong-value")
        with self.assertRaisesRegex(CatalogError, "alias value does not match"):
            validate_model(model, self.official, self.runtime)

    def test_static_evidence_cannot_back_runtime_alias(self):
        model = self.model("ucg-max.json")
        self.add_alias(model, "sysid", "Qualcomm IPQ5322", evidence_id="runtime-static-ucg-max-processor-model-20260830")
        with self.assertRaisesRegex(CatalogError, "aliases require qualified controller/SSH identity evidence"):
            validate_model(model, self.official, self.runtime)

    def test_runtime_alias_source_and_identifier_type_must_match(self):
        model = self.model("ucg-max.json")
        self.add_alias(model, "ssh_model", "Fixture API")
        with self.assertRaisesRegex(CatalogError, "controller evidence cannot prove ssh_model"):
            validate_model(model, self.official, self.runtime)

    def test_missing_runtime_evidence_fails(self):
        model = self.model("ucg-max.json")
        self.add_alias(model, "sysid", "fixture-sysid", evidence_id="runtime-does-not-exist")
        with self.assertRaisesRegex(CatalogError, "evidence reference does not exist"):
            validate_model(model, self.official, self.runtime)

    def test_schema_violation_does_not_reach_semantic_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary) / "catalog"
            shutil.copytree(ROOT, temporary_root)
            path = temporary_root / "models" / "ucg-max.json"
            model = json.loads(path.read_text(encoding="utf-8"))
            model["schema_only_extra"] = True
            path.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(CatalogError, "JSON Schema validation failed"):
                validate_catalog(temporary_root)

    def test_semantic_violation_is_checked_after_schema(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary) / "catalog"
            shutil.copytree(ROOT, temporary_root)
            path = temporary_root / "models" / "ucg-max.json"
            model = json.loads(path.read_text(encoding="utf-8"))
            model["official_evidence_ids"] = ["official-udw-techspecs-20260830"]
            path.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(CatalogError, "official evidence SKU mismatch"):
                validate_catalog(temporary_root)

    def test_secret_scanner_failure_is_not_reported_as_pass(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "secret_scan.py"), str(ROOT / "does-not-exist")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_SCAN=FAIL", result.stdout)
        self.assertNotIn("SECRET_SCAN=PASS", result.stdout)

    def test_local_validation_fails_closed_when_scanner_fails(self):
        from unittest.mock import patch
        with patch("tools.catalog.scan_paths", side_effect=RuntimeError("scanner unavailable")):
            with self.assertRaisesRegex(CatalogError, "secret scanner failed closed"):
                validate_catalog(ROOT)

    def test_deterministic_catalog_serialization(self):
        first = canonical_json(normalized_catalog(self.models))
        second = canonical_json(normalized_catalog(self.models))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
