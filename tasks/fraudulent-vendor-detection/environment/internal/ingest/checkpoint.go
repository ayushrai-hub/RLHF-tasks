package ingest

import (
	"encoding/json"
	"os"
	"sort"

	"vendorlab/internal/util"
)

type Checkpoint struct {
	LastPeriod    int64            `json:"last_period_index"`
	Committed     map[string]int64 `json:"committed_pts"`
	Pending       map[string]int64 `json:"pending_pts"`
	NextBindSlot  int                `json:"next_bind_slot"`
	RejectedCount int                `json:"rejected_count"`
	Lines         []RowView          `json:"lines"`
	Ticks         []TickSnap         `json:"ticks"`
	StateDigest   string             `json:"state_digest"`
}

func SaveCheckpoint(path string, ckpt Checkpoint) error {
	parts := make([]string, 0, len(ckpt.Committed))
	for id, val := range ckpt.Committed {
		parts = append(parts, id+":"+formatInt(val))
	}
	sort.Strings(parts)
	ckpt.StateDigest = util.Digest(parts...)
	data, err := json.MarshalIndent(ckpt, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	return os.WriteFile(path, data, 0o644)
}

func LoadCheckpoint(path string) (Checkpoint, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Checkpoint{}, err
	}
	var ckpt Checkpoint
	if err := json.Unmarshal(data, &ckpt); err != nil {
		return Checkpoint{}, err
	}
	return ckpt, nil
}

func formatInt(v int64) string {
	if v == 0 {
		return "0"
	}
	neg := v < 0
	if neg {
		v = -v
	}
	buf := make([]byte, 0, 20)
	for v > 0 {
		buf = append(buf, byte('0'+v%10))
		v /= 10
	}
	for i, j := 0, len(buf)-1; i < j; i, j = i+1, j-1 {
		buf[i], buf[j] = buf[j], buf[i]
	}
	if neg {
		return "-" + string(buf)
	}
	return string(buf)
}
