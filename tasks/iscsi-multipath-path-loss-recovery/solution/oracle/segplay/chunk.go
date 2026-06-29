package segplay

import (
	"crypto/sha256"
	"encoding/hex"
	"sort"
	"strings"

	"pathfb/caplog"
	"pathfb/model"
)

func chunk(ctx model.Context, ledger *model.Ledger, lim model.Limits) (model.ReplayResult, error) {
	_ = lim
	caplog.ClearStagingTail(ctx.ScenarioLabel)
	if !ctx.CrashMid {
		ledger.ReplayEpoch = 0
		return model.ReplayResult{Ordered: true, Depth: 0}, nil
	}
	segs := append([]model.Segment(nil), ledger.Segments...)
	sort.Slice(segs, func(i, j int) bool {
		return segs[i].Seq < segs[j].Seq
	})
	depth := 0
	for _, seg := range segs {
		if seg.Kind == "dataplane" {
			ledger.ActivePathMask = seg.Mask
			depth++
		}
	}
	for _, seg := range segs {
		if seg.Kind == "affinity" {
			ledger.AffinityMask = seg.Mask & ledger.ActivePathMask
			depth++
		}
	}
	ledger.ReplayEpoch = depth
	ledger.Replayed = true
	return model.ReplayResult{Ordered: true, Depth: depth}, nil
}

// SegmentSeqCRC fingerprints checkpoint segment kinds listed for the pack.
func SegmentSeqCRC(ledger *model.Ledger) string {
	if len(ledger.Segments) == 0 {
		return "0"
	}
	var parts []string
	for _, seg := range ledger.Segments {
		parts = append(parts, seg.Kind)
	}
	sum := sha256.Sum256([]byte(strings.Join(parts, ",")))
	return hex.EncodeToString(sum[:4])
}

// Run exposes crash replay to the sweep package.
func Run(ctx model.Context, ledger *model.Ledger) (model.ReplayResult, error) {
	return chunk(ctx, ledger, model.Limits{MaxSegments: 6})
}
