package cli

import (
	"encoding/json"
	"os"
	"path/filepath"

	"nfrd.local/nfrd/emit"
	"nfrd.local/nfrd/ledger"
	"nfrd.local/nfrd/windowfuse"
	"nfrd.local/nfrd/model"
	"nfrd.local/nfrd/profiles"
)

func RunAudit(profileName string) {
	spec := profiles.Lookup(profileName)
	seedBatch(spec)
	simulateProfile(spec)
	report := emit.BuildReport(spec)
	emit.WriteReport(profileName, report)
}

func seedBatch(spec model.ProfileSpec) {
	batchPath := ledger.BatchPath(spec.Name)
	if _, err := os.Stat(batchPath); err == nil {
		return
	}
	entries := loadFixtures(spec.FixtureDir)
	ledger.AppendBatch(batchPath, entries)
	ledger.AppendBatch(ledger.ReplayPath(spec.Name), entries)
}

func loadFixtures(dir string) []model.Record {
	var out []model.Record
	files, err := os.ReadDir(dir)
	if err != nil {
		panic(err)
	}
	for _, ent := range files {
		if ent.IsDir() {
			continue
		}
		data, err := os.ReadFile(filepath.Join(dir, ent.Name()))
		if err != nil {
			panic(err)
		}
		var rows []model.Record
		if err := json.Unmarshal(data, &rows); err != nil {
			panic(err)
		}
		out = append(out, rows...)
	}
	return out
}

func simulateProfile(spec model.ProfileSpec) {
	switch spec.Simulate {
	case "halt-mid-batch":
		path := ledger.BatchPath(spec.Name)
		rows := ledger.Load(path)
		if len(rows) > 0 {
			ledger.AppendBatch(path, []model.Record{rows[len(rows)-1]})
			ledger.AppendBatch(ledger.SpillPath(spec.Name), []model.Record{rows[0], rows[len(rows)-1]})
		}
	case "partial-epoch-write":
		windowfuse.SaveEpoch(spec.Name, model.EpochMeta{Epoch: 1, Counter: 3, Tag: "stale"})
		rows := ledger.Load(pathForReplay(spec.Name))
		if len(rows) > 0 {
			ledger.AppendBatch(ledger.ShadowPath(spec.Name), rows)
		}
	default:
	}
}

func pathForReplay(profile string) string {
	return ledger.ReplayPath(profile)
}
