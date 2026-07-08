package model

// Transfer is a single payment from one participant to another, in integer
// cents.
type Transfer struct {
	From        string `json:"from"`
	To          string `json:"to"`
	AmountCents int    `json:"amount_cents"`
}

// Plan is the graded artifact written to plan.json.
type Plan struct {
	SettlementFeeUnits int        `json:"settlement_fee_units"`
	Transfers          []Transfer `json:"transfers"`
}
