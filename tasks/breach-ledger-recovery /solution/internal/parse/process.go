package parse

import (
	"encoding/json"
	"path/filepath"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
)

type processRecord struct {
	Seq      int64  `json:"seq"`
	TS       string `json:"ts"`
	Host     string `json:"host"`
	PID      int64  `json:"pid"`
	User     string `json:"user"`
	Cmd      string `json:"cmd"`
}

func unitM(dir string, ev *model.Evidence, issues *[]model.Issue) {
	lines, err := readLines(filepath.Join(dir, "snapshots.jsonl"))
	if err != nil {
		return
	}
	for _, line := range lines {
		var rec processRecord
		if json.Unmarshal([]byte(line), &rec) != nil {
			continue
		}
		ev.Summary["process_snapshots"]++
		key := normalize.NT3(rec.Host) + ":" + stringKey(rec.PID)
		canon := canonicalJSONLine(line)
		if prev, ok := ev.ProcessKeys[key]; ok && prev != canon {
			model.AddIssue(issues, "process_conflict", "conflicting process snapshot")
		}
		ev.ProcessKeys[key] = canon
		host := normalize.NT3(rec.Host)
		user := normalize.NT2(rec.User)
		detail := normalize.NT1(rec.Cmd)
		attacker := pA0(host, user, detail)
		if attacker != "" {
			addEvent(ev, model.Event{Seq: rec.Seq, TS: rec.TS, Host: host, User: user, Source: "process", Action: "process", Detail: detail, AttackerID: attacker})
		}
	}
}

func stringKey(n int64) string {
	return strconvFormat(n)
}
