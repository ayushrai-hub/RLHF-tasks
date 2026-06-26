package lib

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"lockkit/internal/types"
)

const runtimeDir = "/app/environment/.runtime/journal"

func seedDigest(roots types.Roots) string {
	seeds := append([]string{}, roots.Seeds...)
	sort.Strings(seeds)
	return strings.Join(seeds, ",") + "|" + roots.StorageClass
}

func SeedDigestFor(roots types.Roots) string {
	return seedDigest(roots)
}

func pinsFromNodes(nodes map[string]types.NodeInfo) map[string]string {
	pins := map[string]string{}
	for mod, info := range nodes {
		pins[mod] = info.Version
	}
	return pins
}

func readLedger() types.SlotsLedger {
	path := filepath.Join(runtimeDir, "closure.json")
	ledger := types.SlotsLedger{Slots: map[string]types.ClosureSlot{}}
	data, err := os.ReadFile(path)
	if err != nil {
		return ledger
	}
	_ = json.Unmarshal(data, &ledger)
	if ledger.Slots == nil {
		ledger.Slots = map[string]types.ClosureSlot{}
	}
	return ledger
}

func writeLedger(ledger types.SlotsLedger) error {
	_ = os.MkdirAll(runtimeDir, 0o755)
	data, _ := json.MarshalIndent(ledger, "", "  ")
	return os.WriteFile(filepath.Join(runtimeDir, "closure.json"), append(data, '\n'), 0o644)
}

func SaveLedger(nodeMap types.NodeMap, roots types.Roots) error {
	ledger := readLedger()
	prior := ledger.Slots[nodeMap.EntryID]
	ledger.Slots[nodeMap.EntryID] = types.ClosureSlot{
		SeedDigest:  seedDigest(roots),
		Nodes:       nodeMap.Nodes,
		Pins:        pinsFromNodes(nodeMap.Nodes),
		LinkDigest:  prior.LinkDigest,
		SealedAtGen: prior.SealedAtGen,
	}
	return writeLedger(ledger)
}

func UpdateSlotSeal(entry, linkDigest string, sealedAtGen int) {
	ledger := readLedger()
	slot, ok := ledger.Slots[entry]
	if !ok {
		slot = types.ClosureSlot{Pins: map[string]string{}}
	}
	slot.LinkDigest = linkDigest
	slot.SealedAtGen = sealedAtGen
	ledger.Slots[entry] = slot
	_ = writeLedger(ledger)
}

func LoadCached(entry string, roots types.Roots) (types.NodeMap, bool) {
	ledger := readLedger()
	if len(ledger.Slots) == 0 {
		return types.NodeMap{}, false
	}
	slot, ok := ledger.Slots[entry]
	if !ok || len(slot.Nodes) == 0 {
		return types.NodeMap{}, false
	}
	if slot.SeedDigest != seedDigest(roots) {
		return types.NodeMap{}, false
	}
	return types.NodeMap{
		EntryID:      entry,
		StorageClass: roots.StorageClass,
		Nodes:        slot.Nodes,
	}, true
}

func TouchEpoch(entry string) {
	state := ReadEpochState()
	state[entry] = state[entry] + 1
	data, _ := json.MarshalIndent(state, "", "  ")
	_ = os.WriteFile(filepath.Join(runtimeDir, "epoch.json"), append(data, '\n'), 0o644)
}

func TouchReplayGen() {
	gen := ReadReplayGen() + 1
	data, _ := json.MarshalIndent(types.ReplayGen{Gen: gen}, "", "  ")
	_ = os.WriteFile(filepath.Join(runtimeDir, "replay_gen.json"), append(data, '\n'), 0o644)
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

func ReadSlot(entry string) (types.ClosureSlot, bool) {
	ledger := readLedger()
	slot, ok := ledger.Slots[entry]
	return slot, ok
}
