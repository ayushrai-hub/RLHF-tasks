package parse

import "breach-ledger/internal/model"

func unitJ(_ string, ev *model.Evidence, _ *[]model.Issue) {
	ev.Summary["secret_fragments"] = 0
}
