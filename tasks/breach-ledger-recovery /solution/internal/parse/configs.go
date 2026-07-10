package parse

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"

	"breach-ledger/internal/bag"
	"breach-ledger/internal/model"
)

func unitL(dir string, ev *model.Evidence, _ *[]model.Issue) {
	data, err := os.ReadFile(filepath.Join(dir, "manifest.json"))
	if err != nil {
		return
	}
	expected := map[string]string{}
	if json.Unmarshal(data, &expected) != nil {
		return
	}
	for _, name := range bag.SortedKeys(expected) {
		live, err := os.ReadFile(filepath.Join(dir, "live", name))
		if err != nil {
			continue
		}
		sum := sha256.Sum256(live)
		actual := hex.EncodeToString(sum[:])
		ev.Summary["config_files"]++
		if actual != expected[name] {
			addString(&ev.ModifiedConfigs, name)
		}
	}
}
