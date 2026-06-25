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

	if err := verifyCheckpointChain(dir); err != nil {
		return Output{}, err
	}

	prevDigest, err := archiveHeadCheckpoint(dir)
	if err != nil {
		return Output{}, err
	}

	cp := finalizeCheckpoint(Checkpoint{
		SchemaVersion:     checkpointSchemaVersion,
		Seq:               ledger.Seq,
		RunID:             ledger.RunID,
		ConfigGen:         ledger.ConfigGen,
		ScopeGen:          ledger.ScopeGen,
		BucketFingerprint: fingerprintFromTokenMap(ledger.BucketTokens),
	}, prevDigest)
	if err := writeCheckpoint(dir, cp); err != nil {
		return Output{}, err
	}

	return Output{
		Accepted:     snap.Accepted,
		Selected:     snap.SelectedBackend,
		TokensLeft:   snap.TokensLeft,
		StateDigest: balance.StateDigest(
			ledger.BucketTokens,
			ledger.ConfigGen,
			ledger.RouteCounter,
			ledger.ScopeGen,
			ledger.Seq,
			ledger.DigestPendingCount,
		),
		PendingCount: len(s.Meta.PendingReloads),
		LastRunID:    snap.RunID,
		ConfigGen:    snap.ConfigGen,
		ScopeGen:     snap.ScopeGen,
	}, nil
}
