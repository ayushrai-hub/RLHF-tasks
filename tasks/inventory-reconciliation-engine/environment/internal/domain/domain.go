package domain

import "regexp"

const GeneratedFrom = "quota-ledger-v2"

var (
	EventIDRe   = regexp.MustCompile(`^QE-[A-Z0-9]{6}$`)
	AccountIDRe = regexp.MustCompile(`^ACC-[A-Z0-9]{4,8}$`)
	ReplicaRe   = regexp.MustCompile(`^REP-[A-Z0-9]{3,6}$`)
)

var AllowedFields = map[string]struct{}{
	"event_id": {}, "account_id": {}, "operation": {}, "amount": {},
	"logical_time": {}, "source_replica": {}, "seq": {}, "epoch": {},
	"target_event_id": {}, "expires_at": {},
}

var AmountOps = map[string]struct{}{
	"RESERVE": {}, "CONSUME": {}, "RELEASE": {}, "CORRECTION": {},
}

var MutatingOps = map[string]struct{}{
	"RESERVE": {}, "CONSUME": {}, "RELEASE": {}, "REVERSAL": {},
	"SUSPEND": {}, "RESUME": {}, "CORRECTION": {}, "CARRY_FORWARD": {},
}

var RejectionRanks = map[string]int{
	"missing_required":            1,
	"unexpected_fields":           2,
	"invalid_types":               3,
	"invalid_event_id":            4,
	"invalid_account_id":          5,
	"invalid_source_replica":      6,
	"invalid_operation":           7,
	"invalid_logical_time":        8,
	"invalid_seq":                 9,
	"invalid_epoch":               10,
	"invalid_amount":              11,
	"missing_target":              12,
	"invalid_target":              13,
	"duplicate_event_id":          14,
	"stale_seq":                   15,
	"account_suspended":           16,
	"account_not_suspended":       17,
	"resume_replica_mismatch":     18,
	"insufficient_quota":          19,
	"replica_conflict":            20,
	"reversal_account_suspended":  21,
	"reversal_self":               22,
	"reversal_replica_mismatch":   23,
	"reversal_cross_account":      24,
	"reversal_target_missing":     25,
	"reversal_target_not_applied": 26,
	"reversal_already_reversed":   27,
	"reversal_invalid_target":     28,
}
