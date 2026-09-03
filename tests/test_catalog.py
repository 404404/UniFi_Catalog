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

    def test_qualified_runtime_aliases_resolve_to_exact_skus(self):
        cases = (
            ("udw.json", "api_model", "UniFi Dream Wall"),
            ("udw.json", "ssh_model", "Annapurna Labs Alpine V2 UBNT"),
            ("udw.json", "sysid", "0xea2a"),
            ("ucg-max.json", "api_model", "UCG Max"),
            ("ucg-max.json", "ssh_model", "Qualcomm Technologies, Inc. IPQ5332/AP-MI03.1"),
            ("usw-flex-mini.json", "api_model", "USW Flex Mini"),
        )
        for filename, identifier_type, value in cases:
            with self.subTest(identifier_type=identifier_type, value=value):
                model = self.model(filename)
                self.assertIs(resolve_model([model], value, identifier_type=identifier_type), model)

    def test_udw_physical_port_topology_and_unknown_roles_are_explicit(self):
        model = self.model("udw.json")
        ports = {port["index"]: port for port in model["ports"]["items"]}
        self.assertEqual(len(ports), 20)
        self.assertEqual(sorted(ports), list(range(1, 21)))
        for index in range(1, 17):
            self.assertEqual((ports[index]["label"], ports[index]["connector"], ports[index]["max_speed_mbps"]), (f"Port {index}", "rj45", 1000))
        self.assertEqual((ports[17]["connector"], ports[17]["max_speed_mbps"]), ("sfp_plus", 10000))
        self.assertEqual((ports[18]["connector"], ports[18]["max_speed_mbps"]), ("rj45", 1000))
        self.assertEqual((ports[19]["connector"], ports[19]["max_speed_mbps"]), ("rj45", 2500))
        self.assertEqual((ports[20]["connector"], ports[20]["max_speed_mbps"]), ("sfp_plus", 10000))
        for index in range(17, 21):
            self.assertEqual(ports[index]["roles"], [])
            self.assertIsNone(ports[index]["poe_in"])
            self.assertIsNone(ports[index]["poe_out"])
            self.assertIsNone(ports[index]["poe_standard"])
            self.assertIsNone(ports[index]["poe_max_power_w"])

    def test_flex_25g_input_port_is_catalog_qualified(self):
        ports = {port["index"]: port for port in self.model("usw-flex-2.5g-8.json")["ports"]["items"]}
        self.assertFalse(ports[1]["poe_in"])
        self.assertTrue(ports[9]["poe_in"])
        self.assertEqual(ports[9]["poe_standard"], "poe+")
        self.assertFalse(ports[9]["poe_out"])

    def test_qsfp28_connector_is_supported_by_schema_and_semantics(self):
        model = self.model("usw-flex-2.5g-8.json")
        model["ports"]["items"][0]["connector"] = "qsfp28"
        validate_model(model, self.official, self.runtime)

    def test_udw_poe_mapping_by_physical_index(self):
        ports = {port["index"]: port for port in self.model("udw.json")["ports"]["items"]}
        for index in range(1, 5):
            self.assertEqual(
                (ports[index]["poe_out"], ports[index]["poe_standard"], ports[index]["poe_max_power_w"]),
                (True, "poe", 15.4),
            )
        for index in range(5, 9):
            self.assertEqual(
                (ports[index]["poe_out"], ports[index]["poe_standard"], ports[index]["poe_max_power_w"]),
                (True, "poe+", 30),
            )
        for index in range(9, 13):
            self.assertEqual(
                (ports[index]["poe_out"], ports[index]["poe_standard"], ports[index]["poe_max_power_w"]),
                (True, "poe++", 60),
            )
        for index in range(13, 17):
            self.assertEqual(
                (ports[index]["poe_out"], ports[index]["poe_standard"], ports[index]["poe_max_power_w"]),
                (False, None, None),
            )

    def test_qualified_api_aliases_resolve_to_exact_skus(self):
        cases = (
            ("U6 Mesh", "U6-Mesh"),
            ("U6 IW", "U6-IW"),
            ("AC Mesh", "UAP-AC-M"),
            ("U6 Enterprise IW", "U6-Enterprise-IW"),
            ("USW Pro HD 24", "USW-Pro-HD-24"),
            ("US XG 6 PoE", "US-XG-6POE"),
            ("USW Flex 2.5G 8 PoE", "USW-Flex-2.5G-8-PoE"),
            ("USW Flex", "USW-Flex"),
            ("USW Pro Max 16 PoE", "USW-Pro-Max-16-PoE"),
        )
        for value, expected_sku in cases:
            with self.subTest(value=value):
                model = resolve_model(self.models, value, identifier_type="api_model")
                self.assertIsNotNone(model)
                self.assertEqual(model["canonical_sku"], expected_sku)

    def test_all_physical_port_labels_are_neutral(self):
        for model in self.models:
            with self.subTest(canonical_sku=model["canonical_sku"]):
                self.assertEqual(
                    [port["label"] for port in model["ports"]["items"]],
                    [f"Port {port['index']}" for port in model["ports"]["items"]],
                )

    def test_in_wall_port_roles_and_poe_passthrough_are_typed(self):
        for filename in ("u6-iw.json", "u6-enterprise-iw.json"):
            ports = {port["index"]: port for port in self.model(filename)["ports"]["items"]}
            self.assertEqual(ports[1]["connector"], "rj45")
            self.assertTrue({"lan", "downstream", "poe_passthrough"} <= set(ports[1]["roles"]))
            self.assertFalse(ports[1]["poe_in"])
            self.assertTrue(ports[1]["poe_out"])
            for index in range(2, 5):
                self.assertTrue({"lan", "downstream"} <= set(ports[index]["roles"]))
                self.assertFalse(ports[index]["poe_in"])
                self.assertIsNone(ports[index]["poe_out"])
            self.assertTrue({"lan", "uplink", "data_in"} <= set(ports[5]["roles"]))
            self.assertTrue(ports[5]["poe_in"])
            self.assertFalse(ports[5]["poe_out"])

    def test_static_single_port_topology_survives_missing_runtime_port_observations(self):
        for filename, sku in (("u6-mesh.json", "U6-Mesh"), ("uap-ac-m.json", "UAP-AC-M")):
            model = resolve_model(self.models, sku, explicit_sku=True)
            self.assertIsNotNone(model)
            self.assertEqual(model["ports"]["items"], [{
                "index": 1,
                "label": "Port 1",
                "connector": "rj45",
                "roles": ["lan", "uplink", "data_in"],
                "max_speed_mbps": 1000,
                "poe_in": True,
                "poe_out": False,
                "poe_standard": "poe",
                "poe_max_power_w": None,
                "combo_group": None,
            }])
            runtime_observation = {"interfaces": {}}
            self.assertNotIn("ports", runtime_observation["interfaces"])
            self.assertEqual(len(model["ports"]["items"]), 1)
            self.assertTrue({"lan", "uplink", "data_in"} <= set(model["ports"]["items"][0]["roles"]))

    def test_xg_runtime_controller_budget_is_non_authoritative(self):
        model = self.model("us-xg-6poe.json")
        observation = self.runtime["runtime-us-xg-6poe-controller-poe-budget-20260901"]
        self.assertEqual(observation["kind"], "runtime_controller_observation")
        self.assertEqual(observation["canonical_sku"], "US-XG-6POE")
        self.assertEqual(observation["field_path"], "power.controller_reported_poe_budget_w")
        self.assertEqual(observation["observed_value"], 150)
        self.assertEqual(model["power"]["absolute_max_poe_budget_w"], 170)
        self.assertNotIn(observation["id"], model["official_evidence_ids"])
        self.assertFalse(any(observation["id"] in field["evidence_ids"] for profile in model["power"]["power_profiles"] for field in profile["field_evidence"].values()))

    def test_runtime_controller_observation_cannot_qualify_static_power_field(self):
        model = self.model("us-xg-6poe.json")
        field_evidence = model["power"]["power_profiles"][0]["field_evidence"]["poe_budget_w"]
        field_evidence["evidence_ids"] = ["runtime-us-xg-6poe-controller-poe-budget-20260901"]
        with self.assertRaisesRegex(CatalogError, "dynamic runtime observations cannot qualify static capability"):
            validate_model(model, self.official, self.runtime)

    def test_runtime_controller_observation_cannot_back_runtime_alias(self):
        model = self.model("us-xg-6poe.json")
        self.add_alias(model, "api_model", "controller-budget-observation", evidence_id="runtime-us-xg-6poe-controller-poe-budget-20260901")
        with self.assertRaisesRegex(CatalogError, "aliases require qualified controller/SSH identity evidence"):
            validate_model(model, self.official, self.runtime)

    def test_api_alias_resolution_is_independent_of_offline_runtime_state(self):
        model = resolve_model(self.models, "U6 Enterprise IW", identifier_type="api_model")
        self.assertIsNotNone(model)
        offline_runtime = {"online": False, "api_status": "offline"}
        self.assertFalse(offline_runtime["online"])
        self.assertEqual(model["canonical_sku"], "U6-Enterprise-IW")
        self.assertTrue(model["ports"]["complete"])
        self.assertGreater(len(model["ports"]["items"]), 0)

    def test_rs820_near_match_aliases_remain_unresolved(self):
        for value in ("USW Pro HD 24 PoE", "USW Flex 2.5G 8", "USW Pro Max 16"):
            with self.subTest(value=value):
                self.assertIsNone(resolve_model(self.models, value, identifier_type="api_model"))

    def test_multi_switch_fixture_keeps_runtime_ownership_and_static_join(self):
        fixture = json.loads((ROOT / "fixtures" / "rs820-multi-switch-site.json").read_text(encoding="utf-8"))
        seen_keys = set()
        total_runtime_ports = 0
        for device in fixture["devices"]:
            runtime_indices = device["runtime_port_indices"]
            self.assertEqual(len(runtime_indices), len(set(runtime_indices)))
            model = resolve_model(self.models, device["observed_api_model"], identifier_type="api_model")
            expected_sku = device["expected_canonical_sku"]
            if expected_sku is None:
                self.assertIsNone(model)
                self.assertIsNone(device["catalog_static_port_count"])
            else:
                self.assertIsNotNone(model)
                self.assertEqual(model["canonical_sku"], expected_sku)
                self.assertEqual(len(model["ports"]["items"]), device["catalog_static_port_count"])
            for port_idx in runtime_indices:
                self.assertNotIn((device["device_id"], port_idx), seen_keys)
                seen_keys.add((device["device_id"], port_idx))
            total_runtime_ports += len(runtime_indices)
        self.assertGreater(total_runtime_ports, 64)
        self.assertEqual(total_runtime_ports, fixture["site_port_count"])
        self.assertEqual(len(seen_keys), total_runtime_ports)

    def test_ssh_alias_qualification_does_not_override_static_soc(self):
        model = self.model("ucg-max.json")
        processor_before = copy.deepcopy(model["processor"])
        validate_model(model, self.official, self.runtime)
        self.assertEqual(model["processor"], processor_before)
        self.assertEqual(model["runtime_identifiers"]["ssh_model"][0]["value"], "Qualcomm Technologies, Inc. IPQ5332/AP-MI03.1")
        self.assertNotEqual(model["processor"]["model"], model["runtime_identifiers"]["ssh_model"][0]["value"])

    def test_same_text_in_different_alias_types_is_typed(self):
        model = self.model("ucg-max.json")
        same_text_evidence = self.fixture_runtime()["runtime-fixture-qualified"].copy()
        same_text_evidence["id"] = "runtime-fixture-same-text"
        same_text_evidence["supports"] = {"api_model": "Fixture API", "sysid": "Fixture API"}
        self.runtime[same_text_evidence["id"]] = same_text_evidence
        self.add_alias(model, "api_model", "Fixture API", evidence_id=same_text_evidence["id"])
        self.add_alias(model, "sysid", "Fixture API", evidence_id=same_text_evidence["id"])
        validate_model(model, self.official, self.runtime)
        self.assertIs(resolve_model([model], "Fixture API", identifier_type="api_model"), model)
        self.assertIs(resolve_model([model], "Fixture API", identifier_type="sysid"), model)
        self.assertIsNone(resolve_model([model], "Fixture API", identifier_type="ssh_model"))

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

    def test_duplicate_verified_alias_fails_for_each_identifier_type(self):
        for identifier_type in ("api_model", "sysid", "ssh_model"):
            with self.subTest(identifier_type=identifier_type):
                with tempfile.TemporaryDirectory() as temporary:
                    temporary_root = Path(temporary) / "catalog"
                    shutil.copytree(ROOT, temporary_root)
                    identifier_slug = identifier_type.replace("_", "-")
                    value = "same-verified-" + identifier_slug
                    kind = "qualified_ssh" if identifier_type == "ssh_model" else "qualified_controller"
                    for filename, sku in (("ucg-max.json", "UCG-Max"), ("udw.json", "UDW")):
                        evidence_id = "runtime-fixture-duplicate-" + identifier_slug + "-" + sku.lower()
                        evidence = {
                            "id": evidence_id,
                            "kind": kind,
                            "canonical_sku": sku,
                            "supports": {identifier_type: value},
                            "observed_on": "2026-08-31",
                            "source_note": "Synthetic CI fixture; sanitized identity only.",
                        }
                        runtime_path = temporary_root / "evidence" / "runtime" / (evidence_id + ".json")
                        runtime_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
                        path = temporary_root / "models" / filename
                        model = json.loads(path.read_text(encoding="utf-8"))
                        self.add_alias(model, identifier_type, value, evidence_id=evidence_id)
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

    def test_u6_enterprise_iw_port_speeds_match_official_topology(self):
        model = self.model("u6-enterprise-iw.json")
        ports = {port["index"]: port["max_speed_mbps"] for port in model["ports"]["items"]}
        self.assertEqual(ports, {1: 1000, 2: 1000, 3: 1000, 4: 1000, 5: 2500})

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

    def test_requested_poe_budgets_and_profiles_are_explicit(self):
        self.assertEqual(self.model("us-xg-6poe.json")["power"]["absolute_max_poe_budget_w"], 170)
        self.assertEqual(self.model("usw-pro-max-16-poe.json")["power"]["absolute_max_poe_budget_w"], 180)
        flex_25 = self.model("usw-flex-2.5g-8-poe.json")
        self.assertEqual(flex_25["power"]["absolute_max_poe_budget_w"], 196)
        self.assertEqual(
            {profile["id"]: profile["poe_budget_w"] for profile in flex_25["power"]["power_profiles"]},
            {"poe-plus": 16, "poe-plus-plus": 46, "poe-plus-plus-plus": 76, "ac-adapter-210w": 196, "dc-60w": None, "dc-210w": None},
        )
        flex = self.model("usw-flex.json")
        self.assertEqual(flex["power"]["absolute_max_poe_budget_w"], 46)
        self.assertEqual(
            {profile["id"]: profile["poe_budget_w"] for profile in flex["power"]["power_profiles"]},
            {"poe": 8, "poe-plus": 20, "poe-plus-plus": 46, "poe-adapter-60w": 46},
        )

    def test_all_output_poe_class_wattages_are_normalized(self):
        expected = {"poe": 15.4, "poe+": 30, "poe++": 60, "poe+++": 90}
        output_count = 0
        for model in self.models:
            for port in model["ports"]["items"]:
                if port["poe_out"] is True and port["poe_standard"] is not None:
                    output_count += 1
                    self.assertEqual(port["poe_max_power_w"], expected[port["poe_standard"]])
        self.assertGreater(output_count, 0)

    def test_invalid_normalized_output_wattages_are_rejected(self):
        for filename, invalid in (("usw-flex.json", 25), ("usw-pro-max-16-poe.json", 32), ("usw-flex-2.5g-8-poe.json", 64)):
            model = self.model(filename)
            port = next(port for port in model["ports"]["items"] if port["poe_out"] is True and port["poe_standard"] is not None)
            port["poe_max_power_w"] = invalid
            with self.subTest(filename=filename, invalid=invalid):
                with self.assertRaisesRegex(CatalogError, "does not match normalized"):
                    validate_model(model, self.official, self.runtime)
        model = self.model("usw-flex-2.5g-8-poe.json")
        port = next(port for port in model["ports"]["items"] if port["poe_standard"] == "poe++" and port["poe_out"] is True)
        port["poe_max_power_w"] = 64
        with self.assertRaisesRegex(CatalogError, "does not match normalized"):
            validate_model(model, self.official, self.runtime)
        model = self.model("usw-pro-hd-24-poe.json")
        port = next(port for port in model["ports"]["items"] if port["poe_standard"] == "poe++" and port["poe_out"] is True)
        port["poe_standard"] = "poe+++"
        port["poe_max_power_w"] = 95
        with self.assertRaisesRegex(CatalogError, "does not match normalized"):
            validate_model(model, self.official, self.runtime)

    def test_known_poe_model_regressions_and_device_budgets(self):
        expected_ports = {
            "udw.json": {("poe", 15.4), ("poe+", 30), ("poe++", 60)},
            "us-xg-6poe.json": {("poe++", 60)},
            "usw-enterprise-8-poe.json": {("poe+", 30)},
            "usw-flex.json": {("poe+", 30)},
            "usw-flex-2.5g-8-poe.json": {("poe++", 60)},
            "usw-pro-hd-24-poe.json": {("poe++", 60)},
            "usw-pro-max-16-poe.json": {("poe+", 30), ("poe++", 60)},
            "usw-pro-max-24-poe.json": {("poe+", 30), ("poe++", 60)},
        }
        expected_budgets = {
            "udw.json": 420,
            "us-xg-6poe.json": 170,
            "usw-enterprise-8-poe.json": 120,
            "usw-flex.json": 46,
            "usw-flex-2.5g-8-poe.json": 196,
            "usw-pro-hd-24-poe.json": 600,
            "usw-pro-max-16-poe.json": 180,
            "usw-pro-max-24-poe.json": 400,
        }
        for filename, expected in expected_ports.items():
            model = self.model(filename)
            actual = {(port["poe_standard"], port["poe_max_power_w"]) for port in model["ports"]["items"] if port["poe_out"] is True and port["poe_standard"] is not None}
            self.assertEqual(actual, expected)
            self.assertEqual(model["power"]["absolute_max_poe_budget_w"], expected_budgets[filename])

    def test_input_only_poe_ports_keep_output_wattage_unknown(self):
        for model in self.models:
            for port in model["ports"]["items"]:
                if port["poe_in"] is True and port["poe_out"] is False:
                    self.assertIsNone(port["poe_max_power_w"])

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
