# Physical-port semantics

Only physical Ethernet interfaces belong in `ports.items`. Wi-Fi radios are
not ports. Every item has an integer physical index, connector, possible role,
static maximum speed and explicit PoE fields.

Port labels are neutral (`Port N`). Functional roles such as `downstream`,
`uplink`, `data_in` and `poe_passthrough` are typed in `roles`; an empty
`roles` array means no functional role is qualified. `poe_in` and `poe_out`
describe static capability, not runtime enabled/disabled state. For output ports,
`poe_standard` is the normalized IEEE-style class and `poe_max_power_w` is the
normalized nominal PSE maximum for that class: 15.4/30/60/90 W for
PoE/PoE+/PoE++/PoE+++. Input-only ports may retain a null output wattage.

`ports.complete=true` means that the physical Ethernet interface set is fully
enumerated. It does not permit inventing a missing per-port speed or PoE
detail: those details remain `null` when the authoritative source does not
identify them.

For a complete table, all `poe_out=false` means authoritative no PoE output.
If the table is incomplete or contains only unknown PoE direction values,
PoE output is unknown. A combo group must contain at least two physical
connectors and represents mutually exclusive members of one logical path.
