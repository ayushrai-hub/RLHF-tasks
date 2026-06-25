package session

import (
	"gateway-session/balance"
)

// PublishOutput builds the run envelope directly from in-memory store fields.
// Legacy path retained for tooling; the production export hot path is
// export_stage.go reading admission-snapshot.json per admission-snapshot.md.
func PublishOutput(s *Store, accepted bool, selected string, tokensLeft int) Output {
	tokenView := make(map[string]int, len(s.State.Buckets))
	for id, b := range s.State.Buckets {
		tokenView[id] = b.Tokens
	}
	return Output{
		Accepted:     accepted,
		Selected:     selected,
		TokensLeft:   tokensLeft,
		StateDigest: balance.StateDigest(
			tokenView,
			s.State.ConfigGen,
			s.State.RouteCounter,
			s.State.ScopeGen,
			s.Meta.Seq,
			len(s.Meta.PendingReloads),
		),
		PendingCount: len(s.Meta.PendingReloads),
		LastRunID:    s.Meta.LastRunID,
		ConfigGen:    s.State.ConfigGen,
		ScopeGen:     s.State.ScopeGen,
	}
}
