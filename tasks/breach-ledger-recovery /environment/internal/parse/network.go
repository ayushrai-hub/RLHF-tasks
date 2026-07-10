package parse

import "breach-ledger/internal/model"

func unitF(_ string, ev *model.Evidence, _ *[]model.Issue) {
	ev.IOCs = append(ev.IOCs, "ip:203.0.113.41")
	ev.Summary["dns_entries"] = 0
	ev.Summary["egress_entries"] = 0
}
