package lib

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"

	"lockkit/internal/types"
)

const chainPath = "/app/environment/.runtime/journal/replay_chain.jsonl"

func chainPrefixForAppend() string {
	data, err := os.ReadFile(chainPath)
	if err != nil || len(strings.TrimSpace(string(data))) == 0 {
		return "genesis"
	}
	lines, ok := readRawChainLines(string(data))
	if !ok || len(lines) == 0 {
		return "genesis"
	}
	last := lines[len(lines)-1]
	sum := sha256.Sum256([]byte(last))
	return hex.EncodeToString(sum[:])
}

func AppendChainRecord(entry, linkDigest string, gen int) error {
	_ = os.MkdirAll(filepath.Dir(chainPath), 0o755)
	rec := types.ChainRecord{
		EntryID:     entry,
		Gen:         gen,
		LinkDigest:  linkDigest,
		ChainPrefix: chainPrefixForAppend(),
	}
	line, err := json.Marshal(rec)
	if err != nil {
		return err
	}
	f, err := os.OpenFile(chainPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = f.Write(append(line, '\n'))
	return err
}

func ChainHeadMatches(entry string, gen int) bool {
	lines, ok := ReadChainLines()
	if !ok || len(lines) == 0 {
		return false
	}
	head := lines[len(lines)-1]
	return head.EntryID == entry && head.Gen == gen
}

func ReadChainLines() ([]types.ChainRecord, bool) {
	data, err := os.ReadFile(chainPath)
	if err != nil || len(data) == 0 {
		return nil, true
	}
	rawLines, ok := readRawChainLines(string(data))
	if !ok {
		return nil, false
	}
	var out []types.ChainRecord
	for _, line := range rawLines {
		var rec types.ChainRecord
		if json.Unmarshal([]byte(line), &rec) != nil {
			return nil, false
		}
		out = append(out, rec)
	}
	return out, true
}

func ValidateChainPrefixChain() bool {
	lines, ok := ReadChainLines()
	if !ok {
		return false
	}
	expected := "genesis"
	for _, rec := range lines {
		if rec.ChainPrefix != expected {
			return false
		}
		line, err := json.Marshal(rec)
		if err != nil {
			return false
		}
		sum := sha256.Sum256(line)
		expected = hex.EncodeToString(sum[:])
	}
	return true
}

func readRawChainLines(data string) ([]string, bool) {
	trimmed := strings.TrimRight(data, "\n")
	if trimmed == "" {
		return nil, true
	}
	for _, line := range strings.Split(trimmed, "\n") {
		if line == "" {
			return nil, false
		}
	}
	return strings.Split(trimmed, "\n"), true
}

func ResetChain() error {
	return os.Remove(chainPath)
}
