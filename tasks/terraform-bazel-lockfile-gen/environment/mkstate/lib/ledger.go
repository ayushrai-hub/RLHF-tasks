package lib

import (
	"encoding/json"
	"os"
	"path/filepath"

	"lockkit/internal/types"
)

const runtimeDir = "/app/environment/.runtime/journal"

func SeedDigestFor(_ types.Roots) string {
	return ""
}

func SaveLedger(nodeMap types.NodeMap, roots types.Roots) error {
	_ = roots
	_ = os.MkdirAll(runtimeDir, 0o755)
	path := filepath.Join(runtimeDir, "closure.json")
	ledger := types.SlotsLedger{Slots: map[string]types.ClosureSlot{}}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, &ledger)
	}
	if ledger.Slots == nil {
		ledger.Slots = map[string]types.ClosureSlot{}
	}
	merged := map[string]types.NodeInfo{}
	for _, slot := range ledger.Slots {
		for k, v := range slot.Nodes {
			merged[k] = v
		}
	}
	for k, v := range nodeMap.Nodes {
		merged[k] = v
	}
	ledger.Slots[nodeMap.EntryID] = types.ClosureSlot{
		SeedDigest: "",
		Nodes:      merged,
		Pins:       map[string]string{},
	}
	data, _ := json.MarshalIndent(ledger, "", "  ")
	return os.WriteFile(path, append(data, '\n'), 0o644)
}

func UpdateSlotSeal(_ string, _ string, _ int) {}

func LoadCached(entry string, roots types.Roots) (types.NodeMap, bool) {
	_ = roots
	path := filepath.Join(runtimeDir, "closure.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return types.NodeMap{}, false
	}
	var ledger types.SlotsLedger
	if json.Unmarshal(data, &ledger) != nil || len(ledger.Slots) == 0 {
		return types.NodeMap{}, false
	}
	merged := map[string]types.NodeInfo{}
	for _, slot := range ledger.Slots {
		for k, v := range slot.Nodes {
			merged[k] = v
		}
	}
	if len(merged) == 0 {
		return types.NodeMap{}, false
	}
	return types.NodeMap{
		EntryID:      entry,
		StorageClass: roots.StorageClass,
		Nodes:        merged,
	}, true
}

func TouchEpoch(entry string) {
	_ = os.MkdirAll(runtimeDir, 0o755)
	path := filepath.Join(runtimeDir, "epoch.json")
	state := map[string]int{}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, &state)
	}
	state[entry] = state[entry]
	data, _ := json.MarshalIndent(state, "", "  ")
	_ = os.WriteFile(path, append(data, '\n'), 0o644)
}

func TouchReplayGen() {
	_ = os.MkdirAll(runtimeDir, 0o755)
	path := filepath.Join(runtimeDir, "replay_gen.json")
	gen := types.ReplayGen{}
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, &gen)
	}
	data, _ := json.MarshalIndent(gen, "", "  ")
	_ = os.WriteFile(path, append(data, '\n'), 0o644)
}

func ReadEpochState() map[string]int {
	path := filepath.Join(runtimeDir, "epoch.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return map[string]int{}
	}
	state := map[string]int{}
	_ = json.Unmarshal(data, &state)
	return state
}

func ReadReplayGen() int {
	path := filepath.Join(runtimeDir, "replay_gen.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return 0
	}
	gen := types.ReplayGen{}
	_ = json.Unmarshal(data, &gen)
	return gen.Gen
}
