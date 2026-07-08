package settle

import (
	"fmt"

	"tabsettle/model"
)

// Validate checks that a plan obeys the hard settlement rules: positive capped
// amounts, debtor-to-creditor direction only, and every participant settled to
// exactly zero. It returns nil for a valid plan or a descriptive error for the
// first problem found. main uses it to warn on stderr if the program ever emits
// an invalid plan; it does not change the plan.
func Validate(participants []model.Participant, rules model.Rules, plan model.Plan) error {
	bal := make(map[string]int, len(participants))
	for _, p := range participants {
		bal[p.ID] = p.BalanceCents
	}
	sent := make(map[string]int)
	recv := make(map[string]int)
	for _, t := range plan.Transfers {
		bf, okf := bal[t.From]
		bt, okt := bal[t.To]
		if !okf || !okt {
			return fmt.Errorf("transfer references unknown participant")
		}
		if t.From == t.To {
			return fmt.Errorf("transfer from a participant to itself")
		}
		if t.AmountCents <= 0 {
			return fmt.Errorf("non-positive transfer amount")
		}
		if t.AmountCents > rules.MaxTransferCents {
			return fmt.Errorf("transfer exceeds max_transfer_cents")
		}
		if bf >= 0 {
			return fmt.Errorf("transfer sent by non-debtor %s", t.From)
		}
		if bt <= 0 {
			return fmt.Errorf("transfer received by non-creditor %s", t.To)
		}
		sent[t.From] += t.AmountCents
		recv[t.To] += t.AmountCents
	}
	for _, p := range participants {
		if p.BalanceCents < 0 && sent[p.ID] != -p.BalanceCents {
			return fmt.Errorf("debtor %s not settled exactly", p.ID)
		}
		if p.BalanceCents > 0 && recv[p.ID] != p.BalanceCents {
			return fmt.Errorf("creditor %s not settled exactly", p.ID)
		}
	}
	return nil
}
