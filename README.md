# UniFi Catalog

UniFi 硬件型号目录 / UniFi hardware model catalog

这是一个独立、证据驱动的 Ubiquiti UniFi 硬件目录，为未来的
HermesStatus 构建时集成提供稳定输入。它维护官方 canonical SKU、静态
物理 Ethernet 端口拓扑、最大端口速率、PoE、存储、电源和已被合格运行时
证据证明的模型标识。

This is an independent, evidence-backed Ubiquiti UniFi hardware catalog. It
is intended to become a stable build-time input for a future HermesStatus
integration. It maintains canonical SKUs, static physical Ethernet topology,
maximum port speeds, PoE, storage, power, and runtime identifiers only after
qualified evidence.

## What this project is / 项目边界

本目录保存静态硬件事实和经过资格确认的模型标识；不保存实时运行状态，
不实现 telemetry collector，也不会在运行时向 GitHub 发起网络请求。

This repository contains static hardware facts and qualified model
identifiers. It does not contain live operational state, implement telemetry
collection, or make runtime network requests to GitHub.

动态 CPU 温度、CPU 使用率、内存、风扇转速、链路速率、磁盘实际存在状态、
controller/API/SSH 传输配置和健康策略仍属于 HermesStatus collection
profile，不属于本目录。

Dynamic CPU temperature, CPU usage, memory, fan RPM, negotiated link speed,
actual media presence, controller/API/SSH transport configuration, and health
policy remain in HermesStatus collection profiles.

## Authority model / 权威模型

`models/` 是维护中的静态模型定义；`evidence/official/` 保存官方来源 URL、
检索日期和简短事实说明；`evidence/runtime/` 只保存脱敏的 API/SSH 身份
观察；`generated/catalog-index.json` 是工具生成的索引，不得手工编辑。

`models/` holds maintained static model definitions. `evidence/official/`
records authoritative URLs, retrieval dates, and short factual notes.
`evidence/runtime/` contains only sanitized API/SSH identity observations.
`generated/catalog-index.json` is generated and must not be edited manually.

官方来源优先级为 Ubiquiti Tech Specs、Ubiquiti Store/UI 产品页、官方
datasheet/PDF 和官方历史文档。社区或第三方资料只能用于 discovery，不能
把 runtime alias 变成 `verified`，也不能覆盖官方硬件事实。

The evidence hierarchy is Ubiquiti Tech Specs, official Store/UI product
pages, official datasheets/PDFs, and official historical documentation.
Community and third-party sources are discovery aids only: they cannot make a
runtime alias `verified` or override an official hardware fact.

## Canonical SKU and runtime aliases / SKU 与运行时别名

每个模型文件以精确的 canonical Ubiquiti SKU 命名，例如
`models/usw-flex.json`。display name、API model、sysid、SSH Model、管理
地址、MAC 前缀和 controller device ID 都不是 canonical identity。

Each model file is named from the exact canonical Ubiquiti SKU, for example
`models/usw-flex.json`. A display name, API model, sysid, SSH Model,
management address, MAC prefix, or controller device ID is not canonical
identity.

运行时标识位于 `runtime_identifiers`，每条 alias 必须声明 `candidate` 或
`verified`、provenance 和 evidence ID。只有 `verified` alias 才能被 resolver
使用；匹配必须完全相等，顺序为 verified sysid、verified API model、verified
SSH Model，最后才是在调用者明确声明官方 SKU 时匹配 canonical SKU。

Runtime identifiers live under `runtime_identifiers`. Every alias declares
`candidate` or `verified`, provenance, and an evidence ID. Only `verified`
aliases are resolver inputs. Matching is exact and ordered as verified sysid,
verified API model, verified SSH Model, then canonical SKU only when the caller
explicitly supplies an official SKU.

## Phase 1 batch / 第一批型号

本分支首批录入 15 个官方 SKU：UDW、UCG-Max、USW-Flex、USW-Flex-Mini、
USW-Flex-2.5G-5、USW-Flex-2.5G-8-PoE、USW-Pro-Max-16-PoE、USW-Pro-HD-24、
USW-Enterprise-8-PoE、US-XG-6POE、UAP-AC-M、UAP-IW-HD、U6-IW、
U6-Enterprise-IW、U6-Mesh。请求中的 “AC In-Wall HD” 经官方页面核对为
`In-Wall HD`，canonical SKU 是 `UAP-IW-HD`。

The first batch contains 15 exact official SKUs: UDW, UCG-Max, USW-Flex,
USW-Flex-Mini, USW-Flex-2.5G-5, USW-Flex-2.5G-8-PoE,
USW-Pro-Max-16-PoE, USW-Pro-HD-24, USW-Enterprise-8-PoE, US-XG-6POE,
UAP-AC-M, UAP-IW-HD, U6-IW, U6-Enterprise-IW, and U6-Mesh. The requested
“AC In-Wall HD” was checked against the official page and normalized to
`In-Wall HD`, SKU `UAP-IW-HD`.

运行时 matrix 见 [`docs/runtime-identifier-matrix.md`](docs/runtime-identifier-matrix.md)。在没有合格真实观察时保留 UNKNOWN，不用文件名或已有
profile ID 猜测。

## Adding a model / 添加模型流程

1. Confirm the exact official SKU and normalized filename.
2. Add a structured official evidence record with URL, retrieval date and
   supported fields.
3. Add explicit physical Ethernet port items; do not replace topology with a
   port count. Keep unknown values as `null` and incomplete research as
   `complete=false`.
4. Add only static model facts to `models/`; keep collection and live state out.
5. Add sanitized runtime evidence separately. Start aliases as `candidate`.
6. Run validation, regenerate the index, run tests, build twice and inspect the
   diff and secret scan.

详细规则 / Detailed rules: [`docs/contributing.md`](docs/contributing.md)、
[`docs/model-contract.md`](docs/model-contract.md)、
[`docs/evidence-policy.md`](docs/evidence-policy.md) 和
[`docs/physical-port-semantics.md`](docs/physical-port-semantics.md)。

## Validation and release / 校验与发布

```text
python3 tools/validate_catalog.py
python3 tools/build_catalog.py
python3 tools/validate_catalog.py --check-generated
python3 -m unittest discover -s tests -v
python3 tools/build_catalog.py --check --output-dir /tmp/unifi-catalog-build-one
python3 tools/build_catalog.py --check --output-dir /tmp/unifi-catalog-build-two
```

CI 会校验 JSON/schema、模型与 evidence 引用、canonical 顺序、重复 verified
alias、端口/PoE/storage/fan/combo 语义、secret pattern、生成索引一致性和
双次 byte-identical bundle。

CI validates JSON/schema syntax, model/evidence references, canonical order,
duplicate verified aliases, port/PoE/storage/fan/combo semantics, secret
patterns, generated-index consistency, and two byte-identical bundles.

未来 HermesStatus 只在 image build time 固定引入一个 UniFi_Catalog commit
revision 和 deterministic bundle SHA256；本 Phase 不做 HermesStatus 集成、
package publication、runtime GitHub fetch 或 release。

In the future HermesStatus will vendor one pinned UniFi_Catalog revision and
deterministic bundle SHA256 at image-build time. Phase 1 does not integrate
HermesStatus, publish a package, fetch GitHub at runtime, or create a release.

Legacy profile migration audit: [`docs/hermesstatus-migration-audit.md`](docs/hermesstatus-migration-audit.md).
