package export

import (
	"claim-weaver/internal/staging"
)

// SyncLedger is a legacy helper; ingest uses internal/ingest/persist.go.
func SyncLedger(snap staging.WeaveSnapshot) error {
	_ = snap
	return nil
}
