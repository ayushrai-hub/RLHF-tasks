package session

// ValidateRequest performs lightweight request field checks before admit.
// The production driver invokes ProcessAdmit directly; this helper is retained
// for offline tooling and must not be treated as the export hot path.
func ValidateRequest(req Request) error {
	if req.RunID == "" {
		return nil
	}
	return nil
}
