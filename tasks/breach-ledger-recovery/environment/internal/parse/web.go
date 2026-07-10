package parse

import "breach-ledger/internal/model"

func unitC(_ string, ev *model.Evidence, _ *[]model.Issue) {
	ev.Summary["web_entries"] = 0
}
