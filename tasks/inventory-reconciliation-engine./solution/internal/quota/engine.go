package quota

import (
	"encoding/json"
	"sort"
	"time"

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

func seqKey(accountID, replica string) string {
	return accountID + "|" + replica
}

func (e *Engine) ProcessLines(lines [][]byte) {
	sortable := make([]indexedEvent, 0, len(lines))
	for idx, line := range lines {
		var obj map[string]any
		if json.Unmarshal(line, &obj) != nil {
			continue
		}
		eventID := codec.NormalizeID(codec.StrVal(obj["event_id"]))
		logicalTimeStr := codec.StrVal(obj["logical_time"])
		if logicalTimeStr == "" {
			logicalTimeStr = "1970-01-01T00:00:00Z"
		}
		t, err := codec.ParseLogicalTime(logicalTimeStr)
		if err != nil {
			t = time.Unix(0, 0).UTC()
		}
		sortable = append(sortable, indexedEvent{time: t, eventID: eventID, lineIndex: idx, obj: obj})
	}
	sort.Slice(sortable, func(i, j int) bool {
		a, b := sortable[i], sortable[j]
		if !a.time.Equal(b.time) {
			return a.time.Before(b.time)
		}
		if a.eventID != b.eventID {
			return a.eventID < b.eventID
		}
		return a.lineIndex < b.lineIndex
	})
	for _, row := range sortable {
		e.applyOne(row.obj, row.lineIndex)
	}
}

type indexedEvent struct {
	time      time.Time
	eventID   string
	lineIndex int
	obj       map[string]any
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

	acctView := e.State.Accounts[ev.AccountID]
	if acctView == nil {
		acctView = &AccountState{Limit: 1000, Epoch: ev.Epoch}
	}

	if ev.Operation == "RESERVE" || ev.Operation == "CONSUME" || ev.Operation == "RELEASE" || ev.Operation == "CORRECTION" {
		if acctView.Suspended {
			e.reject(ev.EventID, ev.AccountID, "account_suspended")
			return
		}
	}

	if ev.Operation == "RESUME" {
		if !acctView.Suspended {
			e.reject(ev.EventID, ev.AccountID, "account_not_suspended")
			return
		}
		if acctView.SuspendedByReplica != "" && acctView.SuspendedByReplica != ev.SourceReplica {
			e.reject(ev.EventID, ev.AccountID, "resume_replica_mismatch")
			return
		}
	}

	sk := seqKey(ev.AccountID, ev.SourceReplica)
	if prev := e.State.SeqHighwater[sk]; ev.Seq <= prev {
		e.reject(ev.EventID, ev.AccountID, "stale_seq")
		return
	}

	if ev.Operation == "CORRECTION" {
		ck := ev.AccountID + "|" + ev.LogicalTimeStr
		if winner, ok := e.State.CorrectionAtTime[ck]; ok && winner != ev.SourceReplica {
			e.reject(ev.EventID, ev.AccountID, "replica_conflict")
			return
		}
	}

	if ev.Operation == "REVERSAL" {
		if acctView.Suspended {
			e.reject(ev.EventID, ev.AccountID, "reversal_account_suspended")
			return
		}
		if ev.TargetEventID == ev.EventID {
			e.reject(ev.EventID, ev.AccountID, "reversal_self")
			return
		}
		if _, ok := e.State.Reversed[ev.TargetEventID]; ok {
			e.reject(ev.EventID, ev.AccountID, "reversal_already_reversed")
			return
		}
		target := e.State.Applied[ev.TargetEventID]
		if target == nil {
			reason := "reversal_target_missing"
			if _, ok := e.State.RejectedIDs[ev.TargetEventID]; ok {
				reason = "reversal_target_not_applied"
			}
			e.reject(ev.EventID, ev.AccountID, reason)
			return
		}
		if target.SourceReplica != ev.SourceReplica {
			e.reject(ev.EventID, ev.AccountID, "reversal_replica_mismatch")
			return
		}
		if target.AccountID != ev.AccountID {
			e.reject(ev.EventID, ev.AccountID, "reversal_cross_account")
			return
		}
		if target.Operation == "SUSPEND" || target.Operation == "RESUME" || target.Operation == "REVERSAL" || target.Operation == "CARRY_FORWARD" {
			e.reject(ev.EventID, ev.AccountID, "reversal_invalid_target")
			return
		}
	}

	if ev.Operation == "CONSUME" {
		total := acctView.Available + acctView.Held
		if total-*ev.Amount < 0 {
			e.reject(ev.EventID, ev.AccountID, "insufficient_quota")
			return
		}
	}

	if ev.Operation == "RESERVE" {
		if acctView.Available-*ev.Amount < 0 {
			e.reject(ev.EventID, ev.AccountID, "insufficient_quota")
			return
		}
	}

	if ev.Operation == "RELEASE" {
		if acctView.Held-*ev.Amount < 0 {
			e.reject(ev.EventID, ev.AccountID, "insufficient_quota")
			return
		}
	}

	acct := e.State.Accounts[ev.AccountID]
	if acct == nil {
		acct = &AccountState{Limit: 1000, Epoch: ev.Epoch}
		e.State.Accounts[ev.AccountID] = acct
	}

	switch ev.Operation {
	case "REVERSAL":
		target := e.State.Applied[ev.TargetEventID]
		switch target.Operation {
		case "RESERVE":
			acct.Held -= *target.Amount
			acct.Available += *target.Amount
		case "CONSUME":
			need := *target.Amount
			addHeld := need
			if addHeld > acct.Held {
				addHeld = acct.Held
			}
			acct.Held += addHeld
			acct.Available += need - addHeld
		case "RELEASE":
			acct.Held += *target.Amount
			acct.Available -= *target.Amount
		case "CORRECTION":
			acct.Available = e.State.CorrectionPrevAmt[ev.TargetEventID]
		}
		e.State.Reversed[ev.TargetEventID] = struct{}{}
	case "RESERVE":
		acct.Available -= *ev.Amount
		acct.Held += *ev.Amount
		if ev.ExpiresAt != "" {
			e.State.ReserveExpires[ev.EventID] = ev.ExpiresAt
		}
	case "CONSUME":
		need := *ev.Amount
		fromHeld := need
		if fromHeld > acct.Held {
			fromHeld = acct.Held
		}
		acct.Held -= fromHeld
		acct.Available -= (need - fromHeld)
	case "RELEASE":
		acct.Held -= *ev.Amount
		acct.Available += *ev.Amount
	case "CORRECTION":
		e.State.CorrectionPrevAmt[ev.EventID] = acct.Available
		acct.Available = *ev.Amount
		e.State.CorrectionAtTime[ev.AccountID+"|"+ev.LogicalTimeStr] = ev.SourceReplica
	case "SUSPEND":
		acct.Suspended = true
		acct.SuspendedByReplica = ev.SourceReplica
	case "RESUME":
		acct.Suspended = false
		acct.SuspendedByReplica = ""
	case "CARRY_FORWARD":
		acct.Available += acct.Available
		acct.Held = 0
		acct.Epoch = ev.Epoch
	}

	acct.LastEventID = ev.EventID
	acct.LastLogicalTime = ev.LogicalTimeStr
	if acct.Epoch == 0 {
		acct.Epoch = ev.Epoch
	}
	e.State.Applied[ev.EventID] = ev
	e.State.SeqHighwater[sk] = ev.Seq
	e.AppliedCount++
}

func (e *Engine) ApplyExpirations(now time.Time) {
	type expRow struct {
		eventID string
		expires time.Time
		amount  int
		acctID  string
	}
	var rows []expRow
	for eventID, expStr := range e.State.ReserveExpires {
		if _, reversed := e.State.Reversed[eventID]; reversed {
			continue
		}
		ev := e.State.Applied[eventID]
		if ev == nil || ev.Operation != "RESERVE" {
			continue
		}
		exp, err := codec.ParseLogicalTime(expStr)
		if err != nil || (!now.After(exp) && !now.Equal(exp)) {
			continue
		}
		rows = append(rows, expRow{eventID: eventID, expires: exp, amount: *ev.Amount, acctID: ev.AccountID})
	}
	sort.Slice(rows, func(i, j int) bool {
		if rows[i].expires.Equal(rows[j].expires) {
			return rows[i].eventID < rows[j].eventID
		}
		return rows[i].expires.Before(rows[j].expires)
	})
	for _, row := range rows {
		acct := e.State.Accounts[row.acctID]
		if acct == nil {
			continue
		}
		release := row.amount
		if release > acct.Held {
			release = acct.Held
		}
		acct.Held -= release
		acct.Available += release
		delete(e.State.ReserveExpires, row.eventID)
	}
}

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
	for id, acct := range e.State.Accounts {
		if acct.Suspended {
			continue
		}
		if acct.LastEventID == "" {
			continue
		}
		ids = append(ids, id)
	}
	sort.Strings(ids)
	rows := make([]map[string]any, 0, len(ids))
	for _, id := range ids {
		acct := e.State.Accounts[id]
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
