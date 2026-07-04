package pk_c

import (
	"encoding/json"
	"os"
	"path/filepath"
	"syscall"
)

// IncSeq retrieves the current sequence.
func IncSeq() int {
	raw, err := os.ReadFile("/app/output/inc_store/seed.json")
	if err != nil {
		return 0
	}
	var doc struct {
		Seq int `json:"seq"`
	}
	_ = json.Unmarshal(raw, &doc)
	return doc.Seq
}

// BumpIncSeq increments the sequence atomically using flock and records history.
func BumpIncSeq() error {
	path := "/app/output/inc_store/seed.json"
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	lockPath := "/app/output/inc_store/seed.lock"
	lockFile, err := os.OpenFile(lockPath, os.O_CREATE|os.O_RDWR, 0666)
	if err != nil {
		return err
	}
	defer lockFile.Close()

	if err := syscall.Flock(int(lockFile.Fd()), syscall.LOCK_EX); err != nil {
		return err
	}
	defer syscall.Flock(int(lockFile.Fd()), syscall.LOCK_UN)

	seq := 0
	var history []int
	raw, err := os.ReadFile(path)
	if err == nil {
		var doc struct {
			Seq     int   `json:"seq"`
			History []int `json:"history"`
		}
		if json.Unmarshal(raw, &doc) == nil {
			seq = doc.Seq
			history = doc.History
		}
	}
	seq++
	history = append(history, seq)
	docOut := map[string]any{"seq": seq, "history": history}
	out, err := json.MarshalIndent(docOut, "", "  ")
	if err != nil {
		return err
	}
	tmpOut := path + ".tmp"
	if err := os.WriteFile(tmpOut, out, 0o644); err != nil {
		return err
	}
	return os.Rename(tmpOut, path)
}
