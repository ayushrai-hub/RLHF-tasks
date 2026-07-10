package parse

import (
	"encoding/json"
	"path/filepath"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
	"breach-ledger/internal/wire"
)

type auditFrame struct {
	Seq       int64  `json:"seq"`
	TS        string `json:"ts"`
	ClaimedTS string `json:"claimed_ts"`
	Host      string `json:"host"`
	User      string `json:"user"`
	Kind      string `json:"kind"`
	Action    string `json:"action"`
	Detail    string `json:"detail"`
}

func unitG(dir string, ev *model.Evidence, issues *[]model.Issue) {
	frames, err := wire.W0(filepath.Join(dir, "frames.bin"))
	if err != nil {
		model.AddIssue(issues, "malformed_binary_frame", "invalid audit stream")
		return
	}
	for _, data := range frames {
		var frame auditFrame
		if json.Unmarshal(data, &frame) != nil {
			model.AddIssue(issues, "malformed_binary_frame", "invalid audit json")
			return
		}
		ev.Summary["audit_frames"]++
		host := normalize.NT3(frame.Host)
		user := normalize.NT2(frame.User)
		detail := normalize.NT1(frame.Detail)
		addEvent(ev, model.Event{Seq: frame.Seq, TS: frame.TS, Host: host, User: user, Source: "audit", Action: frame.Action, Detail: detail, AttackerID: pA0(host, user, detail)})
		if frame.ClaimedTS != "" && frame.ClaimedTS != frame.TS {
			ev.TamperedEvents = append(ev.TamperedEvents, model.TamperedEvent{Seq: frame.Seq, Host: host, User: user, ClaimedTS: frame.ClaimedTS, TrueTS: frame.TS, Detail: detail})
		}
	}
}
