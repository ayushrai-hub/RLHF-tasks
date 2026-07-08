// Package settle turns a ledger of net balances into a list of transfers that
// squares everyone up.
package settle

import "tabsettle/model"

// Settle builds a settlement plan for the ledger.
//
// The implementation is a plain global greedy pass: it repeatedly takes the
// participant who owes the most and the participant who is owed the most and
// moves as much as it can between them, capped at MaxTransferCents.
func Settle(participants []model.Participant, rules model.Rules) model.Plan {
	cap := rules.MaxTransferCents
	debt := debtors(participants)
	cred := creditors(participants)

	var transfers []model.Transfer
	i, j := 0, 0
	for i < len(debt) && j < len(cred) {
		amt := min3(debt[i].remaining, cred[j].remaining, cap)
		if amt > 0 {
			transfers = append(transfers, model.Transfer{
				From:        debt[i].id,
				To:          cred[j].id,
				AmountCents: amt,
			})
			debt[i].remaining -= amt
			cred[j].remaining -= amt
		}
		if debt[i].remaining == 0 {
			i++
		}
		if cred[j].remaining == 0 {
			j++
		}
	}
	return model.Plan{Transfers: transfers}
}
