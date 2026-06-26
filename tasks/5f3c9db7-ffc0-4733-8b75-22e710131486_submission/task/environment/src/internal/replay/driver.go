package replay

import (
	"sort"
	"logrecover/internal/clock"
	"logrecover/internal/codec"
	"logrecover/internal/config"
	"logrecover/internal/isolation"
	"logrecover/pkg/merge"
	"logrecover/pkg/membership"
	"logrecover/internal/segment"
	"logrecover/pkg/api"
)

func RunPack(pack api.Pack, defaults config.Defaults) (api.Report, int) {
	clk := clock.New()
	rep := api.Report{
		SchemaVersion:    pack.SchemaVersion,
		RecoveryBudgetMS: pack.RecoveryBudgetMS,
		Scenarios:        make(map[string]api.ScenarioReport),
	}
	totalMS := 0
	for _, sc := range pack.Scenarios {
		sr, elapsed := runScenario(sc, defaults, clk)
		rep.Scenarios[sc.ID] = sr
		totalMS += elapsed
	}
	return rep, totalMS
}

func runScenario(sc api.Scenario, defaults config.Defaults, clk *clock.Sim) (api.ScenarioReport, int) {
	start := clk.NowMS()
	all := make([]api.Event, 0)
	loss := 0
	for _, frames := range sc.Frames {
		frames = segment.CompactFrames(frames)
		evs, l := segment.FramesToEvents(frames)
		loss += l
		all = append(all, evs...)
	}
	sort.Slice(all, func(i, j int) bool {
		return merge.ReconcileLess(all[i], all[j])
	})
	digest := codec.CanonicalDigestHex(all)
	qs := membership.VoteStep(sc.Nodes, sc.HealEpoch)
	healed := isolation.HealedAtEpoch(sc.Nodes, sc.HealEpoch)
	if qs > sc.QuorumNeed {
		healed = true
	}
	_ = defaults.RetryBackoffMS
	clk.AdvanceMS(1)
	elapsed := clk.NowMS() - start
	if elapsed < 1 {
		elapsed = 1
	}
	return api.ScenarioReport{
		CanonicalDigestHex: digest,
		RecoveredEvents:    len(all),
		QuorumSizeSeen:     qs,
		RecoveryElapsedMS:  elapsed,
		DataLossEvents:     loss,
		PartitionHealed:    healed,
		MergeMode:          sc.MergeMode,
	}, elapsed
}
