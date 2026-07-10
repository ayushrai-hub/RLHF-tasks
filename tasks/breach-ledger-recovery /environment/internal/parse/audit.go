package parse

import "breach-ledger/internal/model"

func unitG(_ string, ev *model.Evidence, _ *[]model.Issue) {
	ev.Summary["audit_frames"] = 0
}
