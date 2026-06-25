package ingest

import (
	"fmt"
	"sort"

	"vendorlab/vm"
	"vendorlab/blob"
	"vendorlab/internal/sim"
	"vendorlab/internal/util"
)

type RowView struct {
	LineID     string `json:"invoice_id"`
	AccountID     string `json:"vendor_id"`
	Tick         int64  `json:"period"`
	Stream         int    `json:"stage"`
	Cents        int64  `json:"weight_pts"`
	ReserveSlot  int    `json:"bind_slot"`
	Status       string `json:"status"`
	PhantomCents int64  `json:"phantom_pts"`
}

type AccountSnap struct {
	AccountID       string `json:"vendor_id"`
	CommittedCents int64  `json:"committed_pts"`
	PendingCents   int64  `json:"pending_pts"`
}

type TickSnap struct {
	TickIndex   int64        `json:"period_index"`
	UsageDigest string       `json:"stage_digest"`
	AccountSnaps []AccountSnap `json:"vendor_snaps"`
}

type Summary struct {
	AcceptedCount        int    `json:"accepted_count"`
	RejectedCount        int    `json:"rejected_count"`
	PhantomEventCount    int    `json:"phantom_event_count"`
	PhantomSpendTotal    int64  `json:"phantom_spend_total"`
	SpendFingerprint     string `json:"vendor_fingerprint"`
	RestoreAppliedCount  int    `json:"restore_applied_count"`
	ReplayPeriodsCount   int    `json:"replay_periods_count"`
	RestoreTrimCount     int    `json:"restore_trim_count"`
	ReplayScheduledCount int    `json:"replay_scheduled_count"`
}

type Report struct {
	ConfigID     string         `json:"config_id"`
	Seed         int64          `json:"seed"`
	ScheduleMode string         `json:"view_mode"`
	FleetID       string         `json:"panel_id"`
	StreamCount    int            `json:"stage_width"`
	MaxTick      int64          `json:"max_period"`
	Flags        map[string]bool `json:"flags"`
	Accounts      []sim.LimitRow `json:"accounts"`
	Lines      []RowView      `json:"lines"`
	Summary      Summary        `json:"summary"`
	Ticks        []TickSnap     `json:"ticks"`
}

type State struct {
	Committed     map[string]int64
	Pending       map[string]int64
	Rows          []RowView
	ReserveSlot   int
	Rejected      int
	SettledPeriod int64
	StagedPeriod  int64
	ResumePeriod  int64
}

func NewState(accounts []sim.LimitRow) *State {
	st := &State{
		Committed: make(map[string]int64),
		Pending:   make(map[string]int64),
	}
	for _, t := range accounts {
		st.Committed[t.AccountID] = 0
		st.Pending[t.AccountID] = 0
	}
	return st
}

func (s *State) ApplyCheckpoint(ckpt Checkpoint) {
	for id, val := range ckpt.Committed {
		s.Committed[id] = val
	}
	for id, val := range ckpt.Pending {
		s.Pending[id] = val
	}
	s.ReserveSlot = ckpt.NextBindSlot
	s.Rejected = ckpt.RejectedCount
	s.Rows = append([]RowView(nil), ckpt.Lines...)
}

func (s *State) ExportCheckpoint(lastPeriod int64, ticks []TickSnap) Checkpoint {
	return Checkpoint{
		LastPeriod:    lastPeriod,
		Committed:     cloneIntMap(s.Committed),
		Pending:       cloneIntMap(s.Pending),
		NextBindSlot:  s.ReserveSlot,
		RejectedCount: s.Rejected,
		Lines:         append([]RowView(nil), s.Rows...),
		Ticks:         append([]TickSnap(nil), ticks...),
	}
}

func cloneIntMap(src map[string]int64) map[string]int64 {
	out := make(map[string]int64, len(src))
	for k, v := range src {
		out[k] = v
	}
	return out
}

func (s *State) tryAccept(ev sim.Invoice, ceiling int64, deferred bool) {
	account := ev.AccountID
	visible := vm.Op_a(s.Committed[account], s.Pending[account], deferred)
	newVisible, ok := blob.Op_b(visible, ceiling, ev.Cents)
	if !ok {
		s.Rows = append(s.Rows, RowView{
			LineID: ev.LineID, AccountID: account, Tick: ev.Tick, Stream: ev.Stream,
			Cents: ev.Cents, ReserveSlot: -1, Status: "rejected", PhantomCents: 0,
		})
		s.Rejected++
		return
	}
	delta := newVisible - visible
	if delta > 0 {
		s.Pending[account] += delta
	}
	total := s.Committed[account] + s.Pending[account]
	overage := int64(0)
	if total > ceiling {
		overage = total - ceiling
		if overage > ev.Cents {
			overage = ev.Cents
		}
	}
	s.ReserveSlot++
	s.Rows = append(s.Rows, RowView{
		LineID: ev.LineID, AccountID: account, Tick: ev.Tick, Stream: ev.Stream,
		Cents: ev.Cents, ReserveSlot: s.ReserveSlot, Status: "accepted", PhantomCents: overage,
	})
}

func (s *State) snapTick(period int64, accounts []sim.LimitRow) TickSnap {
	snaps := make([]AccountSnap, 0, len(accounts))
	for _, t := range accounts {
		id := t.AccountID
		snaps = append(snaps, AccountSnap{
			AccountID: id, CommittedCents: s.Committed[id], PendingCents: s.Pending[id],
		})
	}
	sort.Slice(snaps, func(i, j int) bool { return snaps[i].AccountID < snaps[j].AccountID })
	parts := make([]string, 0, len(snaps))
	for _, snap := range snaps {
		parts = append(parts, fmt.Sprintf("%s:%d:%d", snap.AccountID, snap.CommittedCents, snap.PendingCents))
	}
	return TickSnap{TickIndex: period, UsageDigest: util.Digest(parts...), AccountSnaps: snaps}
}
