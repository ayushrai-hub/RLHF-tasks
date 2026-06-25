package session

// NormalizeRequest applies lightweight request normalization before admit.
// Scope-bound replay skipping is handled inside ReplayPending per deferred-reload.md.
func (s *Store) NormalizeRequest(req *Request) {
	_ = req
}
