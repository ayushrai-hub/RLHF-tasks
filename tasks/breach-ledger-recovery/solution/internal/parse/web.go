package parse

import (
	"encoding/json"
	"path/filepath"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
)

type webRecord struct {
	Seq           int64  `json:"seq"`
	TS            string `json:"ts"`
	Host          string `json:"host"`
	Src           string `json:"src"`
	Method        string `json:"method"`
	Path          string `json:"path"`
	Status        int    `json:"status"`
	User          string `json:"user"`
	Vulnerability string `json:"vulnerability"`
}

func unitC(dir string, ev *model.Evidence, _ *[]model.Issue) {
	lines, err := readLines(filepath.Join(dir, "access.jsonl"))
	if err != nil {
		return
	}
	for _, line := range lines {
		var rec webRecord
		if json.Unmarshal([]byte(line), &rec) != nil {
			continue
		}
		ev.Summary["web_entries"]++
		host := normalize.NT3(rec.Host)
		user := normalize.NT2(rec.User)
		attacker := pA0(host, user, rec.Src+" "+rec.Path+" "+rec.Vulnerability)
		if attacker != "" && rec.Vulnerability != "" {
			ev.InitialAccess = append(ev.InitialAccess, model.InitialAccess{
				AttackerID:    attacker,
				Host:          host,
				Vector:        "web_upload_rce",
				Vulnerability: rec.Vulnerability,
				Account:       user,
				SourceIP:      rec.Src,
				Timestamp:     rec.TS,
			})
			addEvent(ev, model.Event{Seq: rec.Seq, TS: rec.TS, Host: host, User: user, Source: "web", Action: "web_exploit", Detail: rec.Method + " " + rec.Path, AttackerID: attacker})
			addString(&ev.IOCs, "ip:"+rec.Src)
			addString(&ev.IOCs, "cve:"+rec.Vulnerability)
			addString(&ev.IOCs, "url:"+rec.Path)
		}
	}
}
