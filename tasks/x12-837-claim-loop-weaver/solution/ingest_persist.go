package ingest

import (
	"claim-weaver/internal/staging"
)

func PersistState(snap staging.WeaveSnapshot) error {
	paths := staging.ResolveStatePaths()
	if err := staging.Write(paths.Snapshot, snap); err != nil {
		return err
	}
	ledger := staging.BuildLedger(snap, paths.Ledger)
	return staging.WriteLedger(paths.Ledger, ledger)
}
