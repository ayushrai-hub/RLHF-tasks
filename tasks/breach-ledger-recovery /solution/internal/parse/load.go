package parse

import (
	"path/filepath"
	"time"

	"breach-ledger/internal/model"
)

func P0(root string) (model.Evidence, []model.Issue) {
	ev := model.NewEvidence()
	var issues []model.Issue
	unitA(filepath.Join(root, "inventory"), &ev, &issues)
	unitB(filepath.Join(root, "logs"), &ev, &issues)
	unitC(filepath.Join(root, "web"), &ev, &issues)
	unitD(filepath.Join(root, "histories"), &ev, &issues)
	unitE(filepath.Join(root, "persistence"), &ev, &issues)
	unitF(filepath.Join(root, "network"), &ev, &issues)
	unitG(filepath.Join(root, "audit"), &ev, &issues)
	unitH(filepath.Join(root, "deleted"), &ev, &issues)
	unitI(filepath.Join(root, "git"), &ev, &issues)
	unitJ(filepath.Join(root, "secrets"), &ev, &issues)
	unitK(filepath.Join(root, "archives"), &ev, &issues)
	unitL(filepath.Join(root, "configs"), &ev, &issues)
	unitM(filepath.Join(root, "proc"), &ev, &issues)
	unitN(filepath.Join(root, "containers"), &ev, &issues)
	pL0(&ev, &issues)
	return ev, issues
}

func pL0(ev *model.Evidence, issues *[]model.Issue) {
	seen := map[string]model.InitialAccess{}
	for _, access := range ev.InitialAccess {
		seen[access.AttackerID] = access
	}
	if _, ok := seen["A"]; !ok {
		model.AddIssue(issues, "missing_required_evidence", "missing attacker A initial access")
	}
	if _, ok := seen["B"]; !ok {
		model.AddIssue(issues, "missing_required_evidence", "missing attacker B initial access")
	}
	for _, event := range ev.Events {
		access, ok := seen[event.AttackerID]
		if !ok || event.AttackerID == "" || event.TS == "" || access.Timestamp == "" {
			continue
		}
		et, eerr := time.Parse(time.RFC3339, event.TS)
		at, aerr := time.Parse(time.RFC3339, access.Timestamp)
		if eerr == nil && aerr == nil && et.Before(at) {
			model.AddIssue(issues, "timeline_conflict", "attacker event predates initial access")
			return
		}
	}
}
