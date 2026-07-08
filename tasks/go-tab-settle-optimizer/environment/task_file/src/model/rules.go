package model

// Rules holds the hard limits a settlement plan must respect, loaded from
// rules.json.
type Rules struct {
	// MaxTransferCents is the largest amount any single transfer may move.
	MaxTransferCents    int        `json:"max_transfer_cents"`
	SettlementUnitCents int        `json:"settlement_unit_cents"`
	ForbiddenPairs      []PairRule `json:"forbidden_pairs"`
	CorridorTokens      []string   `json:"corridor_tokens"`
	CorridorLaneTokens  []string   `json:"corridor_lane_tokens"`
}

type PairRule struct {
	From string `json:"from"`
	To   string `json:"to"`
}
