package parse

import "breach-ledger/internal/model"

func unitI(_ string, ev *model.Evidence, _ *[]model.Issue) {
	ev.Summary["git_events"] = 0
}
