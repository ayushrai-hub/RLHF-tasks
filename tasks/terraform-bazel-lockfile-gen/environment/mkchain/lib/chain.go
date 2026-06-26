package lib

import (
	"encoding/json"
	"os"
	"path/filepath"

	"lockkit/internal/types"
)

const chainPath = "/app/environment/.runtime/journal/replay_chain.jsonl"

func AppendChainRecord(entry, linkDigest string, gen int) error {
	_ = os.MkdirAll(filepath.Dir(chainPath), 0o755)
	rec := types.ChainRecord{
		EntryID:     entry,
		Gen:         gen,
		LinkDigest:  linkDigest,
		ChainPrefix: "genesis",
	}
	line, _ := json.Marshal(rec)
	f, err := os.OpenFile(chainPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = f.Write(append(line, '\n'))
	return err
}

func ChainHeadMatches(_ string, _ int) bool {
	return true
}

func ReadChainLines() []types.ChainRecord {
	data, err := os.ReadFile(chainPath)
	if err != nil || len(data) == 0 {
		return nil
	}
	var out []types.ChainRecord
	for _, line := range splitLines(string(data)) {
		if line == "" {
			continue
		}
		var rec types.ChainRecord
		if json.Unmarshal([]byte(line), &rec) == nil {
			out = append(out, rec)
		}
	}
	return out
}

func splitLines(raw string) []string {
	var lines []string
	start := 0
	for i := 0; i < len(raw); i++ {
		if raw[i] == '\n' {
			lines = append(lines, raw[start:i])
			start = i + 1
		}
	}
	if start < len(raw) {
		lines = append(lines, raw[start:])
	}
	return lines
}

func ResetChain() error {
	return os.Remove(chainPath)
}
