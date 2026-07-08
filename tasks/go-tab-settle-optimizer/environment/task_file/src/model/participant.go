package model

// Participant is one person in the shared-tab ledger. BalanceCents is the net
// position: positive means the person is owed money (a creditor), negative
// means the person owes money (a debtor). The whole ledger nets to zero.
type Participant struct {
	ID           string `json:"id"`
	BalanceCents int    `json:"balance_cents"`
	Group        string `json:"group"`
}

// ParticipantFile is the on-disk shape of participants.json.
type ParticipantFile struct {
	Participants []Participant `json:"participants"`
}
