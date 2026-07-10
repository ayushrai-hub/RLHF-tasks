package correlate

import "breach-ledger/internal/model"

func C1(ev model.Evidence) []model.Event {
	return ev.Events
}
