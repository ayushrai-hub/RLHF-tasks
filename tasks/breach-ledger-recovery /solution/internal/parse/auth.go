package parse

import (
	"path/filepath"
	"sort"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
)

func unitB(dir string, ev *model.Evidence, issues *[]model.Issue) {
	files, _ := filepath.Glob(filepath.Join(dir, "auth.log*"))
	sort.Strings(files)
	for _, file := range files {
		lines, err := readLines(file)
		if err != nil {
			continue
		}
		for _, line := range lines {
			m := p1(line)
			if len(m) == 0 {
				continue
			}
			seq := parseInt64(m["seq"])
			if prior, ok := ev.AuthSeq[seq]; ok && prior != line {
				model.AddIssue(issues, "ssh_sequence_violation", "duplicate auth sequence")
			}
			ev.AuthSeq[seq] = line
			ev.Summary["auth_entries"]++
			user := normalize.NT2(m["user"])
			host := normalize.NT3(m["host"])
			if m["event"] == "accepted" && m["method"] == "password" {
				ev.InitialAccess = append(ev.InitialAccess, model.InitialAccess{
					AttackerID:    "A",
					Host:          host,
					Vector:        "ssh_password_spray",
					Vulnerability: "weak_password_reuse",
					Account:       user,
					SourceIP:      m["src"],
					Timestamp:     m["ts"],
				})
				addEvent(ev, model.Event{Seq: seq, TS: m["ts"], Host: host, User: user, Source: "auth", Action: "ssh_login", Detail: "accepted password from " + m["src"], AttackerID: "A"})
				addString(&ev.IOCs, "ip:"+m["src"])
			}
		}
	}
}
