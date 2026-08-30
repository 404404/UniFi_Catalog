# Runtime identity evidence

This directory contains only sanitized controller/SSH observations that are
strong enough to qualify a runtime identifier. No qualified observation was
available for the Phase 1 model batch at catalog creation time, so the model
files intentionally contain empty `api_model`, `sysid` and `ssh_model` alias
lists.

Do not add credentials, tokens, cookies, authorization headers, MAC addresses,
serial numbers, management addresses, controller IDs, raw API payloads or raw
SSH dumps. A candidate identifier may be recorded only with a sanitized
observation and remains unusable by the resolver until independently
qualified.
