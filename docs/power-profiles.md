# Power profiles

V1 separates three facts that must not be collapsed into one power field:

1. `input_method` is the physical input path (`ac_mains`, `ac_adapter`,
   `dc_adapter`, `usb_c`, or `poe`).
2. `input_poe_class` is the negotiated PoE input class when the physical
   input is PoE.
3. `selection_mode` says whether the source is fixed, auto-detected, or
   selected manually in the UniFi controller.

`power.max_device_consumption_w` is maximum device consumption. A profile's
`input_capacity_w` is the capacity of that source or adapter.
`power.absolute_max_poe_budget_w` is the maximum PoE output capability under
any supported source; `power_profiles[].poe_budget_w` is the usable budget for
one source profile.

## Field-level qualification

`power_profiles[].status` qualifies the profile's existence and can be
`verified`, `candidate`, or `unsupported`. Each profile also has independent
`field_evidence` entries for `selection_mode`, `input_method`,
`input_poe_class`, `input_capacity_w`, and `poe_budget_w`. A verified profile
therefore may contain an unknown field:

```json
{
  "id": "dc-60w",
  "status": "verified",
  "selection_mode": "controller_manual",
  "input_method": "dc_adapter",
  "input_poe_class": null,
  "input_capacity_w": 60,
  "poe_budget_w": null,
  "field_evidence": {
    "selection_mode": {"status": "verified", "evidence_ids": []},
    "input_method": {"status": "verified", "evidence_ids": []},
    "input_poe_class": {"status": "not_applicable", "evidence_ids": []},
    "input_capacity_w": {"status": "verified", "evidence_ids": []},
    "poe_budget_w": {"status": "unknown", "evidence_ids": []}
  }
}
```

The complete model files include all five required `field_evidence` entries.
The abbreviated example above shows the complete field map for readability;
its empty `evidence_ids` are paired with the qualification source note in the
maintained model document.
The Flex 2.5G PoE 60W and 210W DC profiles are verified from qualified
controller behavior supplied for V1; their resulting budgets remain `null`
until controller UI/API evidence qualifies them. Unknown budgets are never
coerced to zero.

For non-PoE SKUs, physical port entries explicitly set `poe_out=false`,
`absolute_max_poe_budget_w=0`, and profile PoE budgets are not applicable
(`null`). Sibling models are complete independent documents; no family or
inheritance mechanism participates in resolution.
