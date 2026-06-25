package ingest

import (
	"vendorlab/cord"
	"vendorlab/internal/sim"
	"vendorlab/span"
	"vendorlab/vault"
)

func capturePeriodSnap(st *State) vault.SnapView {
	return vault.SnapView{
		SettledPeriod: st.SettledPeriod,
		StagedPeriod:  st.StagedPeriod,
		ResumePeriod:  st.ResumePeriod,
		NextBindSlot:  st.ReserveSlot,
		RejectedCount: st.Rejected,
		Committed:     cloneIntMap(st.Committed),
		Pending:       cloneIntMap(st.Pending),
	}
}

func applyPeriodSnap(st *State, snap vault.SnapView) int {
	merged := vault.BlendReplica(&snap, &vault.SnapView{
		SettledPeriod: st.SettledPeriod,
		StagedPeriod:  st.StagedPeriod,
		ResumePeriod:  st.ResumePeriod,
		NextBindSlot:  st.ReserveSlot,
		RejectedCount: st.Rejected,
		Committed:     cloneIntMap(st.Committed),
		Pending:       cloneIntMap(st.Pending),
	})
	st.SettledPeriod = merged.SettledPeriod
	st.StagedPeriod = merged.StagedPeriod
	st.ResumePeriod = merged.ResumePeriod
	st.ReserveSlot = merged.NextBindSlot
	st.Rejected = merged.RejectedCount
	for id, val := range merged.Committed {
		st.Committed[id] = val
	}
	for id, val := range merged.Pending {
		st.Pending[id] = val
	}
	return trimRowsAfterRestore(st, st.SettledPeriod, st.StagedPeriod)
}

func trimRowsAfterRestore(st *State, settled, staged int64) int {
	trimmed := 0
	if staged <= settled {
		return 0
	}
	keep := make([]RowView, 0, len(st.Rows))
	for _, row := range st.Rows {
		if row.Tick > settled && row.Tick <= staged {
			trimmed++
			continue
		}
		keep = append(keep, row)
	}
	st.Rows = keep
	return trimmed
}

func (st *State) advanceFrontiers(period int64) {
	st.SettledPeriod, st.StagedPeriod = span.Op_v(st.SettledPeriod, st.StagedPeriod, period)
	st.ResumePeriod = cord.Op_p(st.SettledPeriod, st.StagedPeriod)
}

func stripPeriodRows(st *State, period int64) {
	keep := make([]RowView, 0, len(st.Rows))
	for _, row := range st.Rows {
		if row.Tick != period {
			keep = append(keep, row)
		}
	}
	st.Rows = keep
	st.Rejected = 0
	st.ReserveSlot = 0
	for _, row := range st.Rows {
		if row.Status == "rejected" {
			st.Rejected++
		} else if row.ReserveSlot > st.ReserveSlot {
			st.ReserveSlot = row.ReserveSlot
		}
	}
}

func (st *State) processPeriodBatch(batch []sim.Invoice, ceilings map[string]int64, deferred bool, mode string) {
	if mode == "line_item" {
		for _, ev := range batch {
			ceiling := ceilings[ev.AccountID]
			st.tryAccept(ev, ceiling, deferred)
			st.flushAccount(ev.AccountID, mode)
		}
		return
	}
	for _, ev := range batch {
		ceiling := ceilings[ev.AccountID]
		st.tryAccept(ev, ceiling, deferred)
	}
	st.flushAllFromLimits(ceilings, mode)
}

func (st *State) flushAllFromLimits(ceilings map[string]int64, mode string) {
	for account := range ceilings {
		st.flushAccount(account, mode)
	}
}
