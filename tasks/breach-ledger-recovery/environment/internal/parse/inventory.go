package parse

import "breach-ledger/internal/model"

func unitA(_ string, ev *model.Evidence, _ *[]model.Issue) {
	ev.Summary["users"] = 0
	ev.Summary["hosts"] = 0
}
