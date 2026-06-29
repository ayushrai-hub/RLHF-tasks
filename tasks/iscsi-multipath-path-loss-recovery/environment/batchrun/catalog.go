package batchrun

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"pathfb/queue"
	"pathfb/emit"
	"pathfb/epoch"
	"pathfb/alua"
	"pathfb/model"
	"pathfb/spread"
	"pathfb/segplay"
	"pathfb/retain"
	"pathfb/caplog"
	"pathfb/route"
	"pathfb/audit"
)

type scenarioSpec struct {
	ScenarioLabel      string `json:"scenario_label"`
	TableGen      uint64 `json:"table_gen"`
	CrashMid       bool   `json:"crash_mid"`
	ActivePathMask  uint64 `json:"active_path_mask"`
	TargetPathMask     uint64 `json:"target_path_mask"`
	StrandedPathMask   uint64 `json:"stranded_path_mask"`
	AluaBaseMs int    `json:"alua_base_ms"`
	FlushBump int    `json:"flush_bump"`
	FailbackEarly bool   `json:"failback_early"`
	SummaryGreenView bool   `json:"summary_green_view"`
	RetainSeq      int    `json:"retain_seq"`
	GateHold       bool   `json:"gate_hold"`
}

// RunAll executes bundled scenarios and returns a path failback report envelope.
func RunAll(scenariosDir string) (model.Envelope, error) {
	entries, err := os.ReadDir(scenariosDir)
	if err != nil {
		return model.Envelope{}, err
	}
	var names []string
	for _, ent := range entries {
		if !ent.IsDir() && filepath.Ext(ent.Name()) == ".json" {
			names = append(names, ent.Name())
		}
	}
	sort.Strings(names)
	rows := make([]model.Row, 0, len(names))
	for _, name := range names {
		row, err := runScenario(filepath.Join(scenariosDir, name))
		if err != nil {
			return model.Envelope{}, fmt.Errorf("%s: %w", name, err)
		}
		rows = append(rows, row)
	}
	return emit.BuildEnvelope(rows), nil
}

func runScenario(path string) (model.Row, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return model.Row{}, err
	}
	var spec scenarioSpec
	if err := json.Unmarshal(raw, &spec); err != nil {
		return model.Row{}, err
	}
	ctx := model.Context{
		ScenarioLabel:      spec.ScenarioLabel,
		TableGen:      spec.TableGen,
		CrashMid:       spec.CrashMid,
		ActivePathMask:  spec.ActivePathMask,
		TargetPathMask:     spec.TargetPathMask,
		StrandedPathMask:   spec.StrandedPathMask,
		AluaBaseMs: spec.AluaBaseMs,
		FlushBump: spec.FlushBump,
		FailbackEarly: spec.FailbackEarly,
		SummaryGreenView: spec.SummaryGreenView,
		RetainSeq:      spec.RetainSeq,
		GateHold:       spec.GateHold,
	}
	if ctx.FlushBump == 0 {
		ctx.FlushBump = epoch.FlushBumpDefault()
	}
	ledger := caplog.OpenLedger(ctx)
	_, _ = segplay.Run(ctx, ledger)
	ms, err := caplog.Commit(ctx, ledger)
	if err != nil {
		return model.Row{}, err
	}
	preSpread := spread.SpreadIndex(ms.Dataplane, ms.Affinity)
	retain.Merge(ctx, &ms)
	tbl := queue.LoadTable(ms.Affinity)
	spreadSnap := spread.SpreadIndex(ms.Dataplane, ms.Affinity)
	snap := model.SpreadView{
		SpreadIndex: spreadSnap,
		EvenLooking: spread.EvenLookingSpread(spreadSnap, ctx.SummaryGreenView),
	}
	routeSnap := snap
	if ctx.FailbackEarly {
		routeSnap.SpreadIndex = preSpread
		routeSnap.EvenLooking = spread.EvenLookingSpread(preSpread, ctx.SummaryGreenView)
	}
	routeTbl := model.RouteTable{AffinityMask: ms.Affinity}
	routeTbl, _ = route.Apply(ctx, routeSnap, routeTbl)
	if !routeTbl.Routed {
		routeTbl.AffinityMask = ms.Affinity
	}
	aff := routeTbl.AffinityMask
	dp := ms.Dataplane
	if !alua.Latch(ctx, ledger) {
		queue.Refresh(&tbl, ctx, dp)
	}
	spreadIdx := audit.Record(preSpread, dp, aff)
	retransmit := spec.AluaBaseMs
	if !spread.IsSubset(aff, dp) {
		retransmit += spec.FlushBump * 7
	}
	if spreadIdx == 0 && spec.SummaryGreenView {
		retransmit += spec.FlushBump * 3
	}
	seqCRC := segplay.SegmentSeqCRC(ledger)
	return emit.BuildRow(
		spec.ScenarioLabel,
		spreadIdx,
		spread.MaskHex(dp),
		spread.MaskHex(aff),
		retransmit,
		spec.TableGen,
		ledger.ReplayEpoch,
		seqCRC,
	), nil
}
