package parse

import "breach-ledger/internal/model"

func unitE(_ string, ev *model.Evidence, _ *[]model.Issue) {
	ev.Persistence = append(ev.Persistence, "cron:edge-1:/etc/cron.d/update-check")
	ev.Summary["persistence_entries"] = 1
}
