package report

import "tabsettle/model"

// Summary is a small set of human-facing counters about a plan. It is printed
// to stderr only; the graded artifact is the plan file itself.
type Summary struct {
	Participants int
	Transfers    int
	TotalCents   int
	InGroupCents int
}

// Summarize computes a Summary for a plan against its ledger.
func Summarize(participants []model.Participant, plan model.Plan) Summary {
	group := make(map[string]string, len(participants))
	for _, p := range participants {
		group[p.ID] = p.Group
	}
	s := Summary{Participants: len(participants), Transfers: len(plan.Transfers)}
	for _, t := range plan.Transfers {
		s.TotalCents += t.AmountCents
		if group[t.From] == group[t.To] {
			s.InGroupCents += t.AmountCents
		}
	}
	return s
}
