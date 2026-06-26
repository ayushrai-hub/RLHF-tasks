package lib

import (
	"encoding/json"
	"os"
	"path/filepath"
)

const replayTailPath = "/app/environment/.runtime/journal/replay_tail.json"

type ReplayTail struct {
	EntryID    string `json:"entry_id"`
	SeedDigest string `json:"seed_digest"`
	LinkDigest string `json:"link_digest"`
	Gen        int    `json:"gen"`
}

func WriteReplayTail(_ string, _ string, _ string, _ int) {}

func ReadReplayTail() (ReplayTail, bool) {
	data, err := os.ReadFile(replayTailPath)
	if err != nil {
		return ReplayTail{}, false
	}
	var tail ReplayTail
	if json.Unmarshal(data, &tail) != nil {
		return ReplayTail{}, false
	}
	return tail, true
}

func RemoveReplayTail() error {
	return os.Remove(replayTailPath)
}

func writeReplayTailFile(tail ReplayTail) error {
	_ = os.MkdirAll(filepath.Dir(replayTailPath), 0o755)
	data, _ := json.MarshalIndent(tail, "", "  ")
	return os.WriteFile(replayTailPath, append(data, '\n'), 0o644)
}
