# HermesStatus migration audit

Audit target: `404404/HermesStatus` at revision
`9ea7819c45bfa5e7f87f3de00dfe498c20e25c82`.

This audit is read-only. The legacy profiles were not copied verbatim and the
HermesStatus repository was not modified. `MIGRATE` means that the value is
represented in the new catalog only after normalization and independent
official-source review. `KEEP` means it remains collection-profile data.
`REVIEW` means the legacy value is not authoritative enough to enter the
catalog unchanged.

## Field-by-field classification

| Source repository | Source revision | Source file | Source field | Migration class | Evidence status | Decision |
|---|---|---|---|---|---|---|
| 404404/HermesStatus | `9ea7819c45bfa5e7f87f3de00dfe498c20e25c82` | `clients/unifi_profiles/udw.json` | `cpu_model` | fixed processor identity | legacy value is not independently authoritative | REVIEW; catalog records only the official Cortex-A57/4-core/1.7 GHz description |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `power.psu_slots` | physical power capability | corroborated by official Tech Specs | MIGRATE as `power.psu_slots=2` |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `power.max_power_w` | static power limit | ambiguous: legacy 550 W is the PSU rating, not the official 532 W max device consumption | REVIEW; catalog uses the official 532 W value |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `power.presence` | runtime presence | dynamic | KEEP in HermesStatus |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `power.sensor_mapping` | diagnostic collection semantics | not a hardware fact | KEEP in HermesStatus |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `storage.sata_ssd.supported` | fixed storage capability | corroborated by official integrated 128 GB SSD | MIGRATE as a fixed `ssd` item |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `storage.sata_ssd.capacity_bytes` | factory-installed storage | corroborated by official Tech Specs | MIGRATE as 128,000,000,000 bytes |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `storage.tf.supported` | removable storage-slot capability | normalized and corroborated by official MicroSD slot | MIGRATE as a `microsd` removable item |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `storage.tf.present` | runtime media presence | presence is not static truth | KEEP; catalog uses official default presence only |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `storage.tf.observed` | runtime observation | observation state | KEEP in HermesStatus |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `storage.nvme.supported` | fixed storage capability | legacy-only negative claim; no sufficient official proof for this negative assertion | REVIEW; not migrated as authoritative |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `storage.*.present` | dynamic storage presence | runtime state | KEEP in HermesStatus |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `storage.*.observed` | runtime observation | runtime state | KEEP in HermesStatus |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `poe.supported` | fixed PoE capability | corroborated by official port layout | MIGRATE structurally into the physical port table; no redundant boolean |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `poe.total_max_power_w` | fixed PoE budget | corroborated by official 420 W PoE budget | MIGRATE as `power.poe_budget_w=420` |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `poe.port_max_power_w` | per-port static PoE capability | legacy values conflict with the official page's class grouping/order and lack a source note | REVIEW; catalog uses independently verified class grouping only |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `cpu_model` | fixed processor identity | legacy/community-level value; official page gives only Cortex-A53/4-core/1.5 GHz | REVIEW; exact Qualcomm model is not authoritative in this revision |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `power.psu_slots` | physical power capability | `0` conflates no internal PSU with external adapter | MIGRATE normalized as external adapter with `psu_slots=null` |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `power.presence` | runtime presence | dynamic/unknown | KEEP in HermesStatus |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `power.sensor_mapping` | diagnostic collection semantics | not a hardware fact | KEEP in HermesStatus |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `power.max_power_w` | static power limit | legacy unknown; official Tech Specs now provides 16.1 W | MIGRATE only from official evidence, not from the legacy null |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `storage.nvme.supported` | fixed storage-slot capability | corroborated by official selectable NVMe slot | MIGRATE as an NVMe user slot |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `storage.nvme.capacity_bytes` | installed storage capacity | legacy null and runtime-dependent | KEEP as unknown installed capacity; catalog records official 2 TB maximum capability |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `storage.nvme.present` | runtime media presence | dynamic | KEEP in HermesStatus |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `storage.nvme.observed` | runtime observation | runtime state | KEEP in HermesStatus |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `storage.sata_ssd.supported` | fixed storage capability | legacy-only negative claim | REVIEW; catalog does not copy unsupported rows simply to satisfy a schema |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `storage.tf.supported` | fixed storage capability | legacy-only negative claim | REVIEW; catalog does not copy unsupported rows simply to satisfy a schema |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `poe.supported` | fixed PoE capability | consistent with complete official five-port layout with no PoE output | MIGRATE by deriving no PoE output from the port table |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `poe.port_max_power_w` | per-port static PoE capability | empty because no output is documented | MIGRATE as an empty output set through the port table |
| 404404/HermesStatus | same | `clients/unifi_profiles/udw.json` | `fans.channels` | runtime/diagnostic fan channels | sensor channels do not prove physical fans | REVIEW; catalog keeps `fans.status=unknown` |
| 404404/HermesStatus | same | `clients/unifi_profiles/ucg-max.json` | `fans.channels` | runtime/diagnostic fan channels | explicit legacy unknown; no physical proof | KEEP in HermesStatus; catalog keeps `fans.status=unknown` |
| 404404/HermesStatus | same | `clients/unifi_profiles/*.json` | `schema_version`, `profile_id`, `platform` | collection-profile metadata | not model capability | KEEP in HermesStatus |
| 404404/HermesStatus | same | `clients/unifi_profiles/*.json` | `generic` | telemetry source selection and formulas | runtime collection configuration | KEEP in HermesStatus |
| 404404/HermesStatus | same | `clients/unifi_profiles/*.json` | `diagnostics` | telemetry source selection | runtime diagnostic configuration | KEEP in HermesStatus |
| 404404/HermesStatus | same | `clients/unifi_profiles/*.json` | `health_policy` | collector health behavior | consumer policy, not hardware truth | KEEP in HermesStatus |

## Schema, loader and test classification

`clients/unifi_profiles/profile.schema.json` is a HermesStatus collection
profile contract, not a hardware catalog contract. Its required `generic`,
`diagnostics`, `health_policy`, dynamic fan presence and fixed three-key
storage shape stay with HermesStatus. The new catalog deliberately allows an
empty complete storage list and does not create unsupported NVMe/SATA/TF rows.

`clients/unifi_profile_loader.py` contains profile loading, source allowlisting,
collection semantics, health-policy validation and dynamic-presence validation.
It is not model data and is not migrated. Its `STORAGE_CAPABILITIES`,
`GENERIC_KEYS`, `KNOWN_SOURCES`, and profile-root requirements remain
HermesStatus implementation contracts.

`clients/test_unifi_profiles.py` verifies those loader/profile contracts. The
tests that assert CPU, power, storage or PoE values are migration leads, not
independent official evidence. Their collection-policy and secret-field tests
remain in HermesStatus. Catalog-specific resolver and deterministic-build
tests live under this repository's `tests/` directory.

## Migration map for future HermesStatus removal

Once a fixed UniFi_Catalog revision and bundle SHA256 are qualified in
HermesStatus, the following legacy fields may be removed or made derived:

| HermesStatus profile area | Future catalog source | Qualification prerequisite |
|---|---|---|
| `cpu_model` and other fixed processor facts | model `processor` | official source coverage for exact chip identity, if exact identity is needed |
| `power.psu_slots`, static max power and PoE budget | model `power` | catalog revision and bundle hash pinned at image build |
| `poe` boolean and per-port power map | model `ports` and derived PoE classification | exact port index/class mapping qualified per model |
| fixed storage capability/capacity | model `storage` | catalog storage completeness semantics consumed by the profile loader |
| any physical fan claim | model `fans` | physical evidence, not merely hwmon/fan channels |

The following must not be removed as a consequence of catalog consumption:

* `generic`, `diagnostics`, `health_policy`, source allowlists and collector
  formulas;
* current storage/PSU presence and runtime telemetry;
* runtime API/SSH transport behavior and sensor/chip expectations;
* any unresolved legacy field marked `REVIEW` above.
