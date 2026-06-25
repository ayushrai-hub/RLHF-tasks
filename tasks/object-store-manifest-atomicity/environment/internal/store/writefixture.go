package store

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"terminal.local/objectmanifest/internal/hashutil"
)

type fixtureObject struct {
	key  string
	body string
}

func WriteScenario(root string, scenario string) error {
	if err := os.RemoveAll(root); err != nil {
		return err
	}
	layout := NewLayout(root)
	if err := os.MkdirAll(layout.ObjectsDir(), 0o755); err != nil {
		return err
	}
	if err := os.MkdirAll(layout.ReceiptsDir(), 0o755); err != nil {
		return err
	}
	switch scenario {
	case "crash-retry":
		return writeCrashRetry(layout)
	case "clean-basic":
		return writeCleanBasic(layout)
	case "empty-prepared":
		return writeBatch(layout, "solo-prepared", 41, "prepared", []fixtureObject{
			{"north/audit", "prepared row\n"},
		})
	default:
		return fmt.Errorf("unknown scenario %q", scenario)
	}
}

func writeCrashRetry(layout Layout) error {
	batches := []struct {
		id      string
		epoch   int
		phase   string
		objects []fixtureObject
	}{
		{"north-0001", 1001, "committed", []fixtureObject{{"customers/a", "north customer a v1\n"}, {"customers/b", "north customer b v1\n"}}},
		{"north-0002", 1002, "committed", []fixtureObject{{"orders/a", "north order a v2\n"}}},
		{"north-0003-crash", 1003, "prepared", []fixtureObject{{"ledger/a", "partial ledger a\n"}, {"ledger/b", "partial ledger b\n"}}},
		{"north-0003-rerun", 1004, "committed", []fixtureObject{{"ledger/a", "committed ledger a\n"}, {"ledger/b", "committed ledger b\n"}, {"ledger/c", "committed ledger c\n"}}},
	}
	for _, batch := range batches {
		if err := writeBatch(layout, batch.id, batch.epoch, batch.phase, batch.objects); err != nil {
			return err
		}
	}
	return nil
}

func writeCleanBasic(layout Layout) error {
	if err := writeBatch(layout, "basic-0001", 11, "committed", []fixtureObject{{"alpha", "alpha payload\n"}, {"beta", "beta payload\n"}}); err != nil {
		return err
	}
	return writeBatch(layout, "basic-0002", 12, "committed", []fixtureObject{{"gamma", "gamma payload\n"}})
}

func writeBatch(layout Layout, batchID string, epoch int, phase string, objects []fixtureObject) error {
	sort.Slice(objects, func(i, j int) bool { return objects[i].key < objects[j].key })
	specs := make([]ObjectSpec, 0, len(objects))
	for _, obj := range objects {
		rel := filepath.ToSlash(filepath.Join("objects", batchID, obj.key+".dat"))
		full := layout.ObjectPath(rel)
		if err := os.MkdirAll(filepath.Dir(full), 0o755); err != nil {
			return err
		}
		data := []byte(obj.body)
		if err := os.WriteFile(full, data, 0o644); err != nil {
			return err
		}
		digest := hashutil.SHA256Hex(data)
		sidecar := full + ".sha256"
		if err := os.WriteFile(sidecar, []byte(fmt.Sprintf("%s  %s\n", digest, rel)), 0o644); err != nil {
			return err
		}
		specs = append(specs, ObjectSpec{LogicalKey: obj.key, RelativePath: rel, Size: int64(len(data)), SHA256: digest})
	}
	receipt := Receipt{SchemaVersion: 1, BatchID: batchID, Phase: phase, Epoch: epoch, Objects: specs}
	raw, err := json.MarshalIndent(receipt, "", "  ")
	if err != nil {
		return err
	}
	raw = append(raw, '\n')
	return os.WriteFile(layout.ReceiptPath(batchID), raw, 0o644)
}
