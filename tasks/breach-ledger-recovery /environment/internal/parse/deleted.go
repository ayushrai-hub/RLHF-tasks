package parse

import "breach-ledger/internal/model"

func unitH(_ string, ev *model.Evidence, _ *[]model.Issue) {
	ev.Summary["deleted_files"] = 0
}
