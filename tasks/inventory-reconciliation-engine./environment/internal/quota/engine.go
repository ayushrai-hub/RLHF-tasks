package quota

import (
	"encoding/json"
	"sort"

	"quotaledger/internal/codec"
	"quotaledger/internal/domain"
)

type AccountState struct {
	Limit              int    `json:"limit"`
	Available          int    `json:"available"`
	Held               int    `json:"held"`
	Suspended          bool   `json:"suspended"`
	SuspendedByReplica string `json:"suspended_by_replica,omitempty"`
	Epoch              int    `json:"epoch"`
	LastEventID        string `json:"last_event_id"`
	LastLogicalTime    string `json:"last_logical_time"`
}

type EngineState struct {
	Accounts           map[string]*AccountState
	SeenEventIDs       map[string]map[string]any
	Applied            map[string]*codec.Event
	RejectedIDs        map[string]struct{}
	Reversed           map[string]struct{}
	SeqHighwater       map[string]int
	CorrectionAtTime   map[string]string
	CorrectionPrevAmt  map[string]int
	ReserveExpires     map[string]string
}

type Engine struct {
	State                *EngineState
	AppliedCount         int
	RejectedCount        int
	SkippedIdempotent    int
	Rejections           []codec.Rejection
	EventLineCount       int
	ParsedCount          int
	MalformedLineCount   int
}

func NewEngine() *Engine {
	return &Engine{State: &EngineState{
		Accounts:          map[string]*AccountState{},
		SeenEventIDs:      map[string]map[string]any{},
		Applied:           map[string]*codec.Event{},
		RejectedIDs:       map[string]struct{}{},
		Reversed:          map[string]struct{}{},
		SeqHighwater:      map[string]int{},
		CorrectionAtTime:  map[string]string{},
		CorrectionPrevAmt: map[string]int{},
		ReserveExpires:    map[string]string{},
	}}
}

func seqKey(accountID, replica, operation string) string {
	return accountID + "|" + replica + "|" + operation
}

// ProcessLines applies events in source file order (ignores logical_time ordering).
func (e *Engine) ProcessLines(lines [][]byte) {
	for idx, line := range lines {
		var obj map[string]any
		if json.Unmarshal(line, &obj) != nil {
			continue
		}
		e.applyOne(obj, idx)
	}
}

func (e *Engine) applyOne(obj map[string]any, lineIndex int) {
	ev, rejection := codec.ValidateEvent(obj)
	if rejection != nil {
		e.Rejections = append(e.Rejections, *rejection)
		e.RejectedCount++
		if rejection.EventID != "" {
			e.State.RejectedIDs[rejection.EventID] = struct{}{}
		}
		return
	}

	canon := codec.CanonicalPayload(obj)
	if prev, ok := e.State.SeenEventIDs[ev.EventID]; ok {
		if !mapsEqual(prev, canon) {
			e.reject(ev.EventID, ev.AccountID, "duplicate_event_id")
		} else {
			e.SkippedIdempotent++
		}
		return
	}
	e.State.SeenEventIDs[ev.EventID] = canon

	acct := e.State.Accounts[ev.AccountID]
	if acct == nil {
		acct = &AccountState{Limit: 1000, Epoch: ev.Epoch}
		e.State.Accounts[ev.AccountID] = acct
	}

	if ev.Operation == "RESERVE" || ev.Operation == "CONSUME" || ev.Operation == "RELEASE" || ev.Operation == "CORRECTION" {
		if acct.Suspended {
			e.reject(ev.EventID, ev.AccountID, "account_suspended")
			return
		}
	}

	if ev.Operation == "RESUME" && !acct.Suspended {
		e.reject(ev.EventID, ev.AccountID, "account_not_suspended")
		return
	}

	sk := seqKey(ev.AccountID, ev.SourceReplica, ev.Operation)
	if prev := e.State.SeqHighwater[sk]; ev.Seq <= prev {
		e.reject(ev.EventID, ev.AccountID, "stale_seq")
		return
	}

	if ev.Operation == "CORRECTION" {
		ck := ev.AccountID + "|" + ev.LogicalTimeStr
		e.State.CorrectionAtTime[ck] = ev.SourceReplica
	}

	if ev.Operation == "REVERSAL" {
		target := e.State.Applied[ev.TargetEventID]
		if target == nil {
			e.reject(ev.EventID, ev.AccountID, "reversal_target_missing")
			return
		}
		if targetID := ev.TargetEventID; targetID == ev.EventID {
			e.reject(ev.EventID, ev.AccountID, "reversal_self")
			return
		}
	}

	if ev.Operation == "CONSUME" || ev.Operation == "RESERVE" || ev.Operation == "RELEASE" {
		if acct.Available-*ev.Amount < 0 && ev.Operation != "CONSUME" {
			e.reject(ev.EventID, ev.AccountID, "insufficient_quota")
			return
		}
	}

	switch ev.Operation {
	case "REVERSAL":
		prev := e.State.CorrectionPrevAmt[ev.TargetEventID]
		acct.Available = prev
		e.State.Reversed[ev.TargetEventID] = struct{}{}
	case "RESERVE":
		acct.Available -= *ev.Amount
		acct.Held += *ev.Amount
	case "CONSUME":
		acct.Available -= *ev.Amount
	case "RELEASE":
		acct.Held -= *ev.Amount
		acct.Available += *ev.Amount
	case "CORRECTION":
		e.State.CorrectionPrevAmt[ev.EventID] = acct.Available
		acct.Available = *ev.Amount
	case "SUSPEND":
		acct.Suspended = true
	case "RESUME":
		acct.Suspended = false
	case "CARRY_FORWARD":
		acct.Epoch = ev.Epoch
	}

	acct.LastEventID = ev.EventID
	acct.LastLogicalTime = ev.LogicalTimeStr
	e.State.Applied[ev.EventID] = ev
	e.State.SeqHighwater[sk] = ev.Seq
	e.AppliedCount++
}

func (e *Engine) ApplyExpirations(_ any) {}

func (e *Engine) reject(eventID, accountID, reason string) {
	e.Rejections = append(e.Rejections, codec.Rejection{
		EventID: eventID, AccountID: accountID, Reason: reason,
		PriorityRank: domain.RejectionRanks[reason],
	})
	e.RejectedCount++
	if eventID != "" {
		e.State.RejectedIDs[eventID] = struct{}{}
	}
}

func (e *Engine) AccountRows() []map[string]any {
	ids := make([]string, 0, len(e.State.Accounts))
	for id := range e.State.Accounts {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	rows := make([]map[string]any, 0, len(ids))
	for _, id := range ids {
		acct := e.State.Accounts[id]
		if acct.Suspended {
			continue
		}
		rows = append(rows, map[string]any{
			"account_id":        id,
			"available":         acct.Available,
			"held":              acct.Held,
			"limit":             acct.Limit,
			"epoch":             acct.Epoch,
			"last_event_id":     acct.LastEventID,
			"last_logical_time": acct.LastLogicalTime,
		})
	}
	return rows
}

func mapsEqual(a, b map[string]any) bool {
	ja, _ := json.Marshal(a)
	jb, _ := json.Marshal(b)
	return string(ja) == string(jb)
}
