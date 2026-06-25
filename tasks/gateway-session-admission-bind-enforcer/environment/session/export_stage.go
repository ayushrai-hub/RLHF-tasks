package session

import (
	"gateway-session/balance"
)

func ExportFromSnapshot(dir string, s *Store) (Output, error) {
	snap, err := ReadAdmissionSnapshot(dir)
	if err != nil {
		return Output{}, err
	}
	ledger, err := ReadEnforcementLedger(dir)
	if err != nil {
		return Output{}, err
	}

	bind, err := ReadAdmissionBind(dir)
	if err != nil {
		return Output{}, err
	}
	if err := VerifyStagingTriple(snap, ledger, bind); err != nil {
		return Output{}, err
	}

	_ = verifyCheckpointChain(dir)
	prevDigest, _ := archiveHeadCheckpoint(dir)

	cp := finalizeCheckpoint(Checkpoint{
		SchemaVersion:     checkpointSchemaVersion,
		Seq:               snap.ConfigGen,
		RunID:             snap.RunID,
		ConfigGen:         snap.ConfigGen,
		ScopeGen:          snap.ScopeGen,
		BucketFingerprint: bucketFingerprint(s.State.Buckets),
	}, prevDigest)
	if err := writeCheckpoint(dir, cp); err != nil {
		return Output{}, err
	}

	pendingForDigest := len(s.Meta.PendingReloads)

	return Output{
		Accepted:     snap.Accepted,
		Selected:     snap.SelectedBackend,
		TokensLeft:   snap.TokensLeft,
		StateDigest: balance.StateDigest(
			ledger.BucketTokens,
			snap.ConfigGen,
			snap.RouteCounter,
			snap.ScopeGen,
			ledger.Seq,
			pendingForDigest,
		),
		PendingCount: len(s.Meta.PendingReloads),
		LastRunID:    ledger.RunID,
		ConfigGen:    snap.ConfigGen,
		ScopeGen:     snap.ScopeGen,
	}, nil
}
