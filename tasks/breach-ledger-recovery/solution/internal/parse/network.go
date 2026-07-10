package parse

import (
	"path/filepath"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
)

func unitF(dir string, ev *model.Evidence, _ *[]model.Issue) {
	if lines, err := readLines(filepath.Join(dir, "dns.log")); err == nil {
		for _, line := range lines {
			m := p1(line)
			if len(m) == 0 {
				continue
			}
			ev.Summary["dns_entries"]++
			host := normalize.NT3(m["host"])
			user := normalize.NT2(m["user"])
			detail := m["query"] + " -> " + m["answer"]
			attacker := pA0(host, user, detail)
			if attacker != "" {
				addString(&ev.IOCs, "domain:"+m["query"])
				addString(&ev.IOCs, "ip:"+m["answer"])
				addEvent(ev, model.Event{Seq: 6500 + int64(ev.Summary["dns_entries"]), TS: m["ts"], Host: host, User: user, Source: "dns", Action: "resolve", Detail: detail, AttackerID: attacker})
			}
		}
	}
	if lines, err := readLines(filepath.Join(dir, "egress.log")); err == nil {
		for _, line := range lines {
			m := p1(line)
			if len(m) == 0 {
				continue
			}
			ev.Summary["egress_entries"]++
			host := normalize.NT3(m["host"])
			user := normalize.NT2(m["user"])
			detail := m["protocol"] + " " + m["dst"]
			attacker := pA0(host, user, detail)
			if attacker != "" {
				bytes := parseInt64(m["bytes"])
				if bytes > ev.Exfiltration.Bytes {
					ev.Exfiltration = model.Exfiltration{DestinationIP: m["dst"], Protocol: m["protocol"], Bytes: bytes, Timestamp: m["ts"]}
				}
				addString(&ev.IOCs, "ip:"+m["dst"])
				addEvent(ev, model.Event{Seq: 6600 + int64(ev.Summary["egress_entries"]), TS: m["ts"], Host: host, User: user, Source: "egress", Action: "connect", Detail: detail, AttackerID: attacker})
			}
		}
	}
}
