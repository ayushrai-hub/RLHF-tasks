package report

import (
	"os"
	"path/filepath"

	"breach-ledger/internal/model"
)

func R2(out string, _ []model.Event) error {
	return os.WriteFile(filepath.Join(out, "attack_timeline.csv"), []byte("seq,ts,host,user,source,action,detail,attacker_id\n"), 0o644)
}
