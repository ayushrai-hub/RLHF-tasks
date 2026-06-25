package session

import (
	"gateway-session/balance"
)

func (s *Store) ProcessAdmit(req Request) error {
	if req.FreshStart {
		s.FreshStart()
	}
	s.Meta.LastRunID = req.RunID
	s.Meta.Seq++

	if req.QueueReload != nil {
		QueueReload(&s.Meta, *req.QueueReload)
	}
	if req.ReplayPending {
		ReplayPending(s, s.applyReload)
	}
	if req.Reload != nil {
		s.applyReload(*req.Reload)
	}

	s.applyRefill()

	accepted := true
	selected := ""
	tokensLeft := 0

	if req.Consume != nil {
		backend := req.Consume.Backend
		if backend == "" {
			weights := make(map[string]int, len(s.State.ActiveConfig.Backends))
			for id, be := range s.State.ActiveConfig.Backends {
				weights[id] = be.Weight
			}
			selected = balance.SelectBackend(weights, s.State.RouteCounter)
			s.State.RouteCounter++
			backend = selected
		}
		bucket, ok := s.State.Buckets[backend]
		if !ok {
			accepted = false
		} else {
			accepted = bucket.TryConsume(req.Consume.Cost)
			s.State.Buckets[backend] = bucket
			tokensLeft = bucket.Tokens
		}
	}

	tokenView := make(map[string]int, len(s.State.Buckets))
	for id, b := range s.State.Buckets {
		tokenView[id] = b.Tokens
	}

	pending := len(s.Meta.PendingReloads)

	if err := WriteAdmissionSnapshot(s.dir, AdmissionSnapshot{
		RunID:              req.RunID,
		Accepted:           accepted,
		SelectedBackend:    selected,
		TokensLeft:         tokensLeft,
		ConfigGen:          s.State.ConfigGen,
		ScopeGen:           s.State.ScopeGen,
		RouteCounter:       s.State.RouteCounter,
		Seq:                s.Meta.Seq,
		DigestPendingCount: pending,
		BucketTokens:       tokenView,
	}); err != nil {
		return err
	}

	ledger := EnforcementLedger{
		RunID:              req.RunID,
		BucketTokens:       tokenView,
		ConfigGen:          s.State.ConfigGen,
		ScopeGen:           s.State.ScopeGen,
		RouteCounter:       s.State.RouteCounter,
		Seq:                s.Meta.Seq,
		DigestPendingCount: pending,
		AdmitSeal: ComputeAdmitSeal(
			req.RunID,
			tokenView,
			s.State.ConfigGen,
			s.State.ScopeGen,
			s.State.RouteCounter,
			s.Meta.Seq,
			pending,
		),
	}
	if err := WriteEnforcementLedger(s.dir, ledger); err != nil {
		return err
	}
	return WriteAdmissionBind(s.dir, ledger)
}
