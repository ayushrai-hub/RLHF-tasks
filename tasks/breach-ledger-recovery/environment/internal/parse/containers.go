package parse

import "breach-ledger/internal/model"

func unitN(_ string, ev *model.Evidence, _ *[]model.Issue) {
	ev.Summary["container_entries"] = 0
}
