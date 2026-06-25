package ingest

import (
	"fmt"
	"sort"

	"vendorlab/internal/app"
	"vendorlab/internal/decoy"
	"vendorlab/internal/sim"
	"vendorlab/internal/util"
	"vendorlab/vault"
)

func flagsMap(f app.Flags) map[string]bool {
	return map[string]bool{
		"multi_stage":       f.MultiStream,
		"strict_stage_sort": f.StrictStreamSort,
		"deferred_rollout":  f.DeferredSettle,
		"track_exposure":    f.TrackAccrual,
	}
}

func Run(envRoot string, cfg app.Config) (Report, error) {
	fleet, err := sim.LoadFleet(envRoot, cfg.FleetID)
	if err != nil {
		return Report{}, err
	}
	ceilings := sim.CeilingMap(fleet.Limits)
	st := NewState(fleet.Limits)
	deferred := cfg.Flags.DeferredSettle && cfg.ScheduleMode == "vendor_graph"

	var prefixTicks []TickSnap
	startPeriod := int64(0)
	if cfg.WarmCheckpoint != "" {
		ckpt, err := LoadCheckpoint(cfg.WarmCheckpoint)
		if err != nil {
			return Report{}, err
		}
		st.ApplyCheckpoint(ckpt)
		prefixTicks = append(prefixTicks, ckpt.Ticks...)
		startPeriod = ckpt.LastPeriod + 1
	}

	var ticks []TickSnap
	var periodSnap *vault.SnapView
	var restoreApplied, replayPeriods, restoreTrim, replayScheduled int

	failover := cfg.FailoverPeriod
	if failover < 1 {
		failover = 1
	}

	for period := startPeriod; period <= cfg.MaxTick; period++ {
		if cfg.RunMode == "period_failover" && period == failover && periodSnap != nil {
			if periodSnap.SettledPeriod < period {
				replayScheduled = int(period - periodSnap.SettledPeriod)
			}
			restoreTrim += applyPeriodSnap(st, *periodSnap)
			restoreApplied++
			for replay := st.ResumePeriod; replay < period; replay++ {
				stripPeriodRows(st, replay)
				batch := linesForTick(fleet.Lines, replay, cfg.StreamCount)
				st.processPeriodBatch(batch, ceilings, deferred, cfg.ScheduleMode)
				replayPeriods++
			}
		}

		batch := linesForTick(fleet.Lines, period, cfg.StreamCount)
		st.processPeriodBatch(batch, ceilings, deferred, cfg.ScheduleMode)
		ticks = append(ticks, st.snapTick(period, fleet.Limits))
		st.advanceFrontiers(period)
		_ = decoy.TickLatency(period, st.Pending[fleet.Limits[0].AccountID])
		_ = decoy.SloHealthy(period, st.Pending[fleet.Limits[0].AccountID])
		_ = decoy.PaymentTermsRate(st.Committed[fleet.Limits[0].AccountID], ceilings[fleet.Limits[0].AccountID])

		if cfg.RunMode == "period_failover" && period == failover-1 {
			snap := capturePeriodSnap(st)
			periodSnap = &snap
		}
	}

	allTicks := append(prefixTicks, ticks...)
	rows := append([]RowView(nil), st.Rows...)
	sort.Slice(rows, func(i, j int) bool { return rows[i].LineID < rows[j].LineID })

	accepted := 0
	overageEvents := 0
	var leaked int64
	fpParts := make([]string, 0, len(rows))
	for _, row := range rows {
		if row.Status == "accepted" {
			accepted++
			if row.PhantomCents > 0 {
				overageEvents++
				leaked += row.PhantomCents
			}
			fpParts = append(fpParts, fmt.Sprintf("%s:%d", row.LineID, row.ReserveSlot))
		}
	}

	summary := Summary{
		AcceptedCount:        accepted,
		RejectedCount:        st.Rejected,
		PhantomEventCount:    overageEvents,
		PhantomSpendTotal:    leaked,
		SpendFingerprint:     util.Digest(fpParts...),
		RestoreAppliedCount:  restoreApplied,
		ReplayPeriodsCount:   replayPeriods,
		RestoreTrimCount:     restoreTrim,
		ReplayScheduledCount: replayScheduled,
	}

	report := Report{
		ConfigID: cfg.ConfigID, Seed: cfg.Seed, ScheduleMode: cfg.ScheduleMode,
		FleetID: cfg.FleetID, StreamCount: cfg.StreamCount, MaxTick: cfg.MaxTick,
		Flags: flagsMap(cfg.Flags), Accounts: fleet.Limits, Lines: rows,
		Summary: summary, Ticks: allTicks,
	}

	if cfg.CheckpointOut != "" {
		lastPeriod := cfg.MaxTick
		ckpt := st.ExportCheckpoint(lastPeriod, allTicks)
		if err := SaveCheckpoint(cfg.CheckpointOut, ckpt); err != nil {
			return Report{}, err
		}
	}

	return report, nil
}
