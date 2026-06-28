package orchestrate

import (
	"sort"

	"nfrd.local/nfrd/model"
)

func ReconcilePhase(state model.ViewState, records []model.Record) model.ViewState {
	rules := map[string]model.RuleView{}
	order := make([]string, 0)
	for _, rec := range records {
		if _, ok := rules[rec.RuleID]; !ok {
			order = append(order, rec.RuleID)
		}
		rules[rec.RuleID] = model.RuleView{
			RuleID:   rec.RuleID,
			Priority: rec.Priority,
			Epoch:    rec.Epoch,
			Mark:     rec.Mark,
		}
	}
	sort.Strings(order)
	out := make([]model.RuleView, 0, len(order))
	for _, id := range order {
		out = append(out, rules[id])
	}
	state.Rules = out
	return state
}
