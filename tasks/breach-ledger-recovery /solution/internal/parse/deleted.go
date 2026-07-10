package parse

import (
	"encoding/json"
	"os/exec"
	"path/filepath"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
)

type deletedRow struct {
	Path        string `json:"path"`
	SHA256      string `json:"sha256"`
	DeletedAt   string `json:"deleted_at"`
	Size        int64  `json:"size"`
	RecoveredBy string `json:"recovered_from"`
}

func unitH(dir string, ev *model.Evidence, issues *[]model.Issue) {
	db := filepath.Join(dir, "deleted.sqlite")
	out, err := exec.Command("sqlite3", "-json", db, "SELECT path, sha256, deleted_at, size, recovered_from FROM deleted_files ORDER BY path, deleted_at").Output()
	if err != nil {
		model.AddIssue(issues, "missing_required_evidence", "deleted sqlite unavailable")
		return
	}
	var rows []deletedRow
	if json.Unmarshal(out, &rows) != nil {
		model.AddIssue(issues, "missing_required_evidence", "deleted sqlite json unavailable")
		return
	}
	for _, row := range rows {
		ev.Summary["deleted_files"]++
		if !normalize.NP1(row.Path) {
			model.AddIssue(issues, "path_traversal", "unsafe deleted path")
			continue
		}
		current := model.DeletedFile{Path: row.Path, SHA256: row.SHA256, DeletedAt: row.DeletedAt, Size: row.Size, RecoveredBy: row.RecoveredBy}
		if prev, ok := ev.DeletedRows[row.Path]; ok && (prev.SHA256 != current.SHA256 || prev.Size != current.Size) {
			model.AddIssue(issues, "deleted_meta_conflict", "conflicting deleted row")
			continue
		}
		ev.DeletedRows[row.Path] = current
		addString(&ev.StolenFiles, row.Path)
	}
}
