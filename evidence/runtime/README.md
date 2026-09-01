# Runtime and device-local evidence

This directory contains only sanitized, structured evidence:

* qualified_controller observations may qualify api_model and sysid;
* runtime_controller_observation records sanitized dynamic controller values and never qualify static model fields or resolver aliases;
* qualified_ssh observations may qualify ssh_model;
* qualified_runtime_static observations may qualify explicitly allowed model-fixed
  fields, currently processor.model.

Every record binds a canonical_sku. Identity evidence also binds an identifier
type and exact observed value through supports; static evidence binds a field
path, observed value, source class and qualification state. Static evidence is
not a resolver alias unless a separate qualified identity record exists.

Do not add credentials, tokens, cookies, authorization headers, MAC addresses,
serial numbers, management addresses, controller IDs, raw API payloads or raw
SSH dumps. Candidate identifiers remain unusable by the resolver until
independently qualified as verified.
