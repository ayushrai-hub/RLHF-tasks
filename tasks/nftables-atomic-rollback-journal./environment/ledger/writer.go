package ledger

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strconv"

	"nfrd.local/nfrd/model"
)

func AppendBatch(path string, rows []model.Record) {
	var prior []model.Record
	if data, err := os.ReadFile(path); err == nil {
		_ = json.Unmarshal(data, &prior)
	}
	merged := append(prior, rows...)
	sort.Slice(merged, func(i, j int) bool { return merged[i].Seq < merged[j].Seq })
	model.WriteJSON(path, merged)
}

func BatchPath(profile string) string {
	return filepath.Join(model.OutDir, "state", profile, "batch.json")
}

func ReplayPath(profile string) string {
	return filepath.Join(model.OutDir, "state", profile, "batch.replay.json")
}

func ShadowPath(profile string) string {
	return filepath.Join(model.OutDir, "state", profile, "batch.shadow.json")
}

func SpillPath(profile string) string {
	return filepath.Join(model.OutDir, "state", profile, "batch.spill.json")
}

func Load(path string) []model.Record {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	var rows []model.Record
	if err := json.Unmarshal(data, &rows); err != nil {
		return nil
	}
	return rows
}

func LoadJournal(profile string) []model.Record {
	return Load(BatchPath(profile))
}

func loadOne(path string) []model.Record {
	return Load(path)
}

func journalKey(rec model.Record) string {
	return rec.RunID + "\x00" + rec.Phase + "\x00" + rec.RuleID + "\x00" + rec.Action + "\x00" + strconv.Itoa(rec.Seq)
}
