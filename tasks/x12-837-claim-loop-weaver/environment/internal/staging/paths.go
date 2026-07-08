package staging

import (
	"os"
	"path/filepath"
)

type StatePaths struct {
	Snapshot string
	Ledger   string
}

func ResolveStatePaths() StatePaths {
	base := "/app/state"
	if override := os.Getenv("TB3_WEAVE_STATE"); override != "" {
		base = override
	}
	return StatePaths{
		Snapshot: filepath.Join(base, "weave-snapshot.json"),
		Ledger:   filepath.Join(base, "weave-ledger.json"),
	}
}
