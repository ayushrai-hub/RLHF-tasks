package emit

import (
	"path/filepath"
	"sort"

	"nfrd.local/nfrd/model"
	"nfrd.local/nfrd/phaseconv"
	"nfrd.local/nfrd/windowfuse"
)

func BuildReport(profile model.ProfileSpec) model.Report {
	auth := windowfuse.Authority(profile.Name)
	var runs []model.RunRecord
	var entries []model.EntryRecord
	for _, runID := range profile.Runs {
		for _, phaseName := range []string{"apply", "settle"} {
			state := phaseconv.RunPhase(profile, runID, phaseName, auth.Epoch)
			hash := model.TreeHash(state.Rules)
			runs = append(runs, model.RunRecord{
				RunID:    runID,
				Phase:    phaseName,
				TreeHash: hash,
			})
			for _, rule := range state.Rules {
				entries = append(entries, model.EntryRecord{
					RuleID:       rule.RuleID,
					Action:       phaseName,
					Epoch:        rule.Epoch,
					ObservedHash: model.ObservedHash(rule),
				})
			}
		}
	}
	sort.Slice(runs, func(i, j int) bool {
		if runs[i].RunID == runs[j].RunID {
			return runs[i].Phase < runs[j].Phase
		}
		return runs[i].RunID < runs[j].RunID
	})
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].RuleID == entries[j].RuleID {
			if entries[i].Epoch == entries[j].Epoch {
				return entries[i].Action < entries[j].Action
			}
			return entries[i].Epoch < entries[j].Epoch
		}
		return entries[i].RuleID < entries[j].RuleID
	})
	return model.Report{
		Profile: profile.Name,
		Epoch:   auth.Epoch,
		Runs:    runs,
		Entries: entries,
	}
}

func WriteReport(profile string, report model.Report) {
	path := filepath.Join(model.OutDir, "audit_report.json")
	model.WriteJSON(path, report)
}

func spanRecord(runID, phaseName, hash string, rows []model.Record) model.CheckpointRecord {
	return model.CheckpointRecord{
		RunID:       runID,
		Phase:       phaseName,
		RecordCount: len(rows),
		TreeHash:    hash,
	}
}
