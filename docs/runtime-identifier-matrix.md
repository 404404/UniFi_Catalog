# Runtime identifier matrix

This matrix records exact qualified runtime observations. The qualified
device-local SoC evidence remains static model evidence, not a resolver alias.
Only exact controller values with verified evidence are resolver inputs.

| Product | Official SKU | API model | sysid | SSH Model | API == SKU? | SSH == SKU? | Qualification status | Evidence |
|---|---|---|---|---|---|---|---|---|
| U6 Enterprise In-Wall | U6-Enterprise-IW | U6 Enterprise IW | UNKNOWN | UNKNOWN | NO | UNKNOWN | VERIFIED | runtime-u6-enterprise-iw-controller-identity-20260901 |
| U6 In-Wall | U6-IW | U6 IW | UNKNOWN | UNKNOWN | NO | UNKNOWN | VERIFIED | runtime-u6-iw-controller-identity-20260901 |
| U6 Mesh | U6-Mesh | U6 Mesh | UNKNOWN | UNKNOWN | NO | UNKNOWN | VERIFIED | runtime-u6-mesh-controller-identity-20260901 |
| AC Mesh | UAP-AC-M | AC Mesh | UNKNOWN | UNKNOWN | NO | UNKNOWN | VERIFIED | runtime-ac-mesh-controller-identity-20260901 |
| In-Wall HD | UAP-IW-HD | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | No qualified observation |
| Cloud Gateway Max | UCG-Max | UCG Max | UNKNOWN | Qualcomm Technologies, Inc. IPQ5332/AP-MI03.1 | NO | UNKNOWN | VERIFIED | runtime-ucg-max-controller-identity-20260831; runtime-ucg-max-ssh-identity-20260831 |
| Dream Wall | UDW | UniFi Dream Wall | 0xea2a | Annapurna Labs Alpine V2 UBNT | NO | NO | VERIFIED | runtime-udw-controller-identity-20260831; runtime-udw-ssh-identity-20260831 |
| XG 6 PoE (Gen1) | US-XG-6POE | US XG 6 PoE | UNKNOWN | UNKNOWN | NO | UNKNOWN | VERIFIED | runtime-us-xg-6poe-controller-identity-20260831 |
| Enterprise 8 PoE (Vintage) | USW-Enterprise-8-PoE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | No qualified observation |
| Flex | USW-Flex | USW Flex | UNKNOWN | UNKNOWN | NO | UNKNOWN | VERIFIED | runtime-usw-flex-controller-identity-20260831 |
| Flex Mini 2.5G | USW-Flex-2.5G-5 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | No qualified observation |
| Flex 2.5G | USW-Flex-2.5G-8 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | No qualified observation |
| Flex 2.5G PoE | USW-Flex-2.5G-8-PoE | USW Flex 2.5G 8 PoE | UNKNOWN | UNKNOWN | NO | UNKNOWN | VERIFIED | runtime-usw-flex-2-5g-8-poe-controller-identity-20260831 |
| Flex Mini | USW-Flex-Mini | USW Flex Mini | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | VERIFIED | runtime-usw-flex-mini-controller-identity-20260831 |
| Pro HD 24 | USW-Pro-HD-24 | USW Pro HD 24 | UNKNOWN | UNKNOWN | NO | UNKNOWN | VERIFIED | runtime-usw-pro-hd-24-controller-identity-20260831 |
| Pro HD 24 PoE | USW-Pro-HD-24-PoE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | No qualified observation |
| Pro Max 16 | USW-Pro-Max-16 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | No qualified observation |
| Pro Max 16 PoE | USW-Pro-Max-16-PoE | USW Pro Max 16 PoE | UNKNOWN | UNKNOWN | NO | UNKNOWN | VERIFIED | runtime-usw-pro-max-16-poe-controller-identity-20260831 |
| Pro Max 24 | USW-Pro-Max-24 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | No qualified observation |
| Pro Max 24 PoE | USW-Pro-Max-24-PoE | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | No qualified observation |

The matrix is maintained separately from static model capability. A future
qualified controller or SSH observation may add a `candidate` alias first; only
`verified` aliases can be used by the production resolver.
