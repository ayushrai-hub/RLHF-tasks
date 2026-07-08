package gate

const (
	ResultAllow = "allow"
	ResultDeny  = "deny"

	ReasonAllowedByGroup       = "allowed-by-group"
	ReasonMissingPrincipal     = "missing-principal"
	ReasonRevokedPrincipal     = "revoked-principal"
	ReasonExpiredEntry         = "expired-cache-entry"
	ReasonMissingRequiredGroup = "missing-required-group"
	ReasonUnprovenRevision     = "unproven-directory-revision"
	ReasonProofExpiredAtAuth   = "proof-expired-at-authorize"
	ReasonStaleCacheEpoch      = "stale-cache-epoch"
	ReasonSubjectMismatch      = "subject-generation-mismatch"
)
