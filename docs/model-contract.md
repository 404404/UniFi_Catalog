# Model contract

Each file in `models/` is keyed by one exact canonical Ubiquiti SKU. The
canonical SKU is stable identity; the display name is descriptive only.

The contract separates:

* official static hardware facts: processor description when officially
  documented, physical Ethernet ports, static maximum speed, PoE direction and
  limits, storage capability and power capability;
* runtime identifier evidence: `api_model`, `sysid` and `ssh_model` aliases,
  each explicitly `candidate` or `verified`;
* runtime operational state: deliberately absent from this repository.

`null` is an explicit unknown value. `complete=false` means research is
incomplete; it does not mean the hardware capability is absent.
