package settle

import (
	"sort"

	"tabsettle/model"
)

// account is a mutable working copy of one participant's outstanding position
// during settlement: remaining is what is still owed (debtor) or still owed to
// them (creditor), always tracked as a positive magnitude.
type account struct {
	id        string
	group     string
	remaining int
}

// debtors returns the participants who owe money, as positive-magnitude
// accounts sorted from largest debt to smallest.
func debtors(ps []model.Participant) []*account {
	var out []*account
	for _, p := range ps {
		if p.BalanceCents < 0 {
			out = append(out, &account{id: p.ID, group: p.Group, remaining: -p.BalanceCents})
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].remaining > out[j].remaining })
	return out
}

// creditors returns the participants who are owed money, as positive-magnitude
// accounts sorted from largest credit to smallest.
func creditors(ps []model.Participant) []*account {
	var out []*account
	for _, p := range ps {
		if p.BalanceCents > 0 {
			out = append(out, &account{id: p.ID, group: p.Group, remaining: p.BalanceCents})
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].remaining > out[j].remaining })
	return out
}
