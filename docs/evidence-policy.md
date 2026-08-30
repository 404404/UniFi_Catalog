# Evidence policy

Official static facts prefer current Ubiquiti Tech Specs, official Store/UI
product pages, official datasheets and official archived documentation.
Community pages and third-party databases may help discovery but cannot
establish an authoritative static fact or a verified runtime matcher.

Runtime aliases need sanitized qualified controller or SSH observations. Keep
only identifier type, observed value, qualified source class and observation
date. Never commit credentials, tokens, cookies, authorization headers, MAC
addresses, serials, management addresses, controller IDs, raw payloads or raw
SSH dumps.

The source URL and retrieval date are stored in `evidence/official/`. Runtime
evidence is stored separately under `evidence/runtime/`.
