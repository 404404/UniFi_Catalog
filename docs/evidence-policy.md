# Evidence policy

Official static facts prefer current Ubiquiti Tech Specs, official Store/UI
product pages, official datasheets and official archived documentation.
Community pages and third-party databases may help discovery but cannot
establish an authoritative static fact or a verified runtime matcher.

Runtime identity aliases need sanitized qualified controller or SSH observations.
Keep only identifier type, observed value, canonical SKU, qualified source class
and observation date. qualified_controller may prove only api_model and sysid;
qualified_ssh may prove only ssh_model. An alias evidence value must equal the
alias value, and its canonical SKU must equal the owning model SKU.

A sanitized qualified_runtime_static record may establish only an explicitly
allowed model field, currently processor.model, when its field path, observed
value, canonical SKU and qualification_state=verified bind to the maintained
model. Static evidence never becomes a runtime resolver alias.

The authoritative Python secret scanner is used by local validation and CI and
fails closed if it cannot scan. evidence/runtime may contain only sanitized
identity observations or explicitly qualified static evidence.
