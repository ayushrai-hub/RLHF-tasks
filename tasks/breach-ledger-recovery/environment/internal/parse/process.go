package parse

import "breach-ledger/internal/model"

func unitM(_ string, ev *model.Evidence, _ *[]model.Issue) {
	ev.Summary["process_snapshots"] = 0
}
