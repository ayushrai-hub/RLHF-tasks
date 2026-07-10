package parse

import (
	"encoding/json"
	"path/filepath"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
)

type containerRecord struct {
	Seq      int64  `json:"seq"`
	TS       string `json:"ts"`
	Host     string `json:"host"`
	ID       string `json:"id"`
	Image    string `json:"image"`
	Command  string `json:"command"`
}

func unitN(dir string, ev *model.Evidence, _ *[]model.Issue) {
	lines, err := readLines(filepath.Join(dir, "list.jsonl"))
	if err != nil {
		return
	}
	for _, line := range lines {
		var rec containerRecord
		if json.Unmarshal([]byte(line), &rec) != nil {
			continue
		}
		ev.Summary["container_entries"]++
		host := normalize.NT3(rec.Host)
		detail := normalize.NT1(rec.Command)
		attacker := pA0(host, "root", rec.ID+" "+rec.Image+" "+detail)
		if attacker != "" {
			addString(&ev.IOCs, "container:"+rec.ID)
			addString(&ev.IOCs, "image:"+rec.Image)
			addEvent(ev, model.Event{Seq: rec.Seq, TS: rec.TS, Host: host, User: "root", Source: "container", Action: "container", Detail: detail, AttackerID: attacker})
		}
	}
}
