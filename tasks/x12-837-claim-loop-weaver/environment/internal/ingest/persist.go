package ingest

import (
	"claim-weaver/internal/staging"
)

// PersistState writes ingest artifacts under /app/state (snapshot only in starter).
func PersistState(snap staging.WeaveSnapshot) error {
	paths := staging.ResolveStatePaths()
	return staging.Write(paths.Snapshot, snap)
}
