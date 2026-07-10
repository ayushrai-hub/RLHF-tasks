package parse

import "breach-ledger/internal/model"

func unitK(_ string, ev *model.Evidence, _ *[]model.Issue) {
	ev.Summary["archive_entries"] = 0
}
