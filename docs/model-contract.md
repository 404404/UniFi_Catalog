# Model contract

Each file in `models/` is keyed by one exact canonical Ubiquiti SKU. The
canonical SKU is stable identity; the display name is descriptive only.

The contract separates:

* qualified device-local static facts: an explicitly bound model field may be established by sanitized qualified_runtime_static evidence;
* official static hardware facts: processor description when officially
  documented, physical Ethernet ports, static maximum speed, PoE direction and
  limits, storage capability and power capability;
* runtime identifier evidence: `api_model`, `sysid` and `ssh_model` aliases,
  each explicitly `candidate` or `verified`;
* runtime operational state: deliberately absent from this repository.

Physical port labels are always neutral (`Port N`). Functional roles are typed
in `ports.items[].roles`; an empty roles array means no functional role is
qualified. `poe_in`, `poe_out` and `poe_passthrough` describe static capability
and never runtime enabled/disabled state.

For output ports, `poe_standard` is the normalized IEEE-style PoE class and
`poe_max_power_w` is its normalized nominal PSE output maximum: PoE 15.4 W,
PoE+ 30 W, PoE++ 60 W and PoE+++ 90 W. Input-only ports may keep
`poe_max_power_w=null`; that field is output power, not input class capacity.
`power.absolute_max_poe_budget_w` is the whole-device maximum available PoE
budget and must not be replaced by `sum(port.poe_max_power_w)`.

`null` is an explicit unknown value. `complete=false` means research is
incomplete; it does not mean the hardware capability is absent.


## Power profiles

`power.max_device_consumption_w` is the model/device maximum consumption and is separate
from per-profile `input_capacity_w`. Each `power_profiles[]` item records one
physical input option or selected source profile:

* `selection_mode=fixed` is a fixed physical source;
* `selection_mode=auto_detected` is negotiated PoE input;
* `selection_mode=controller_manual` is a controller-selected source profile;
* `absolute_max_poe_budget_w` is the maximum model capability;
* `poe_budget_w` is the usable budget for that profile.

`status` qualifies profile existence independently from field evidence. A
profile may be `verified` while an individual field, such as its PoE budget,
is `unknown`; in that case the value is `null`, never an inferred zero.
`field_evidence` records the qualification status and evidence reference for
each power-profile field. Unsupported profiles are never returned by the
production active-profile helper. The structure also represents controller
manual modes used by the USW Ultra family without model inheritance.
