package lib

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"

	"lockkit/internal/types"
)

const outputDir = "/app/output"

func LinkDigest(lock []types.LockRow, checksum []types.ChecksumRow) string {
	checksumMaps := make([]map[string]string, len(checksum))
	for i, row := range checksum {
		checksumMaps[i] = map[string]string{
			"digest":   row.Digest,
			"repo_key": row.RepoKey,
		}
	}
	lockMaps := make([]map[string]string, len(lock))
	for i, row := range lock {
		lockMaps[i] = map[string]string{
			"module_id": row.ModuleID,
			"repo_key":  row.RepoKey,
			"version":   row.Version,
		}
	}
	blob, _ := json.Marshal(map[string]any{
		"checksum": checksumMaps,
		"lock":     lockMaps,
	})
	sum := sha256.Sum256(blob)
	return hex.EncodeToString(sum[:])
}

func OutputArtifactsFresh(entry string, lock []types.LockRow, checksum []types.ChecksumRow) bool {
	dig := LinkDigest(lock, checksum)
	onDisk, ok := ReadOutputLinkDigest()
	if !ok {
		return false
	}
	if onDisk != dig {
		return false
	}
	slot, ok := readSlot(entry)
	if !ok || slot.LinkDigest == "" {
		return false
	}
	return slot.LinkDigest == dig
}

func WriteOutputs(lock types.LockSnapshot, repo map[string]any, checksum map[string]any, stub types.ModuleLockStub) error {
	_ = os.MkdirAll(outputDir, 0o755)
	if err := writeJSON(filepath.Join(outputDir, "lock_snapshot.json"), lock); err != nil {
		return err
	}
	if err := writeJSON(filepath.Join(outputDir, "repo_table.bzl"), repo); err != nil {
		return err
	}
	if err := writeJSON(filepath.Join(outputDir, "checksum_rows.json"), checksum); err != nil {
		return err
	}
	return writeJSON(filepath.Join(outputDir, "module_lock.bzl"), stub)
}

func ReadOutputLinkDigest() (string, bool) {
	lockPath := filepath.Join(outputDir, "lock_snapshot.json")
	checkPath := filepath.Join(outputDir, "checksum_rows.json")
	lockBytes, err := os.ReadFile(lockPath)
	if err != nil {
		return "", false
	}
	checkBytes, err := os.ReadFile(checkPath)
	if err != nil {
		return "", false
	}
	var lock types.LockSnapshot
	var checksum struct {
		Rows []types.ChecksumRow `json:"rows"`
	}
	if json.Unmarshal(lockBytes, &lock) != nil || json.Unmarshal(checkBytes, &checksum) != nil {
		return "", false
	}
	dig := LinkDigest(lock.Rows, checksum.Rows)
	if dig == "" {
		return "", false
	}
	return dig, true
}

func readSlot(entry string) (types.ClosureSlot, bool) {
	path := filepath.Join("/app/environment/.runtime/journal", "closure.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return types.ClosureSlot{}, false
	}
	var ledger types.SlotsLedger
	if json.Unmarshal(data, &ledger) != nil {
		return types.ClosureSlot{}, false
	}
	slot, ok := ledger.Slots[entry]
	return slot, ok
}

func writeJSON(path string, v any) error {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	return os.WriteFile(path, data, 0o644)
}
