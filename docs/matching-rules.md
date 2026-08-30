# Runtime matching rules

The reference resolver uses exact, case-sensitive values and only verified
aliases. Its priority is:

1. verified `sysid`;
2. verified `api_model`;
3. verified `ssh_model`;
4. canonical SKU only when the caller explicitly says that the input is an
   official SKU.

Candidate aliases are never resolved. Display names, management addresses,
MAC prefixes, controller device IDs, array positions and substring/fuzzy
similarity are never resolver inputs.
