package parse

import (
	"encoding/json"
	"path/filepath"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
)

type gitRecord struct {
	CommitID string `json:"commit_id"`
	TS       string `json:"ts"`
	Host     string `json:"host"`
	Author   string `json:"author"`
	Action   string `json:"action"`
	Path     string `json:"path"`
}

func unitI(dir string, ev *model.Evidence, issues *[]model.Issue) {
	lines, err := readLines(filepath.Join(dir, "events.jsonl"))
	if err != nil {
		return
	}
	for _, line := range lines {
		var rec gitRecord
		if json.Unmarshal([]byte(line), &rec) != nil {
			continue
		}
		ev.Summary["git_events"]++
		canon := canonicalJSONLine(line)
		if prev, ok := ev.GitCommits[rec.CommitID]; ok && prev != canon {
			model.AddIssue(issues, "git_history_conflict", "conflicting git commit")
		}
		ev.GitCommits[rec.CommitID] = canon
		host := normalize.NT3(rec.Host)
		user := normalize.NT2(rec.Author)
		attacker := pA0(host, user, rec.Path)
		if attacker != "" {
			addEvent(ev, model.Event{Seq: gitSeq(rec.CommitID), TS: rec.TS, Host: host, User: user, Source: "git", Action: rec.Action, Detail: rec.Path, AttackerID: attacker})
		}
	}
}

func gitSeq(commitID string) int64 {
	seq := int64(6800)
	for _, r := range commitID {
		seq += int64(r)
	}
	return seq
}
