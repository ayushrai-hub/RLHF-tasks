package caplog

import (
	"encoding/json"
	"os"
	"path/filepath"

	"pathfb/model"
)

const stagingRoot = "/app/var/failback_journal"

// OpenLedger initializes checkpoint storage for a pack context.
func OpenLedger(ctx model.Context) *model.Ledger {
	ledger := &model.Ledger{
		ActivePathMask: 0,
		AffinityMask:  ctx.StrandedPathMask,
	}
	if ctx.CrashMid {
		ledger.Segments = []model.Segment{
			{Kind: "affinity", Mask: ctx.StrandedPathMask, Seq: 1},
			{Kind: "dataplane", Mask: ctx.TargetPathMask, Seq: 2},
		}
	} else {
		ledger.Segments = []model.Segment{
			{Kind: "dataplane", Mask: ctx.TargetPathMask, Seq: 1},
		}
	}
	LoadStagingTail(ctx.ScenarioLabel, ledger)
	return ledger
}

// LoadStagingTail merges a persisted replay tail when present.
func LoadStagingTail(label string, ledger *model.Ledger) {
	path := filepath.Join(stagingRoot, label+".tail")
	raw, err := os.ReadFile(path)
	if err != nil {
		return
	}
	var tail struct {
		ReplayEpoch int `json:"replay_epoch"`
	}
	if json.Unmarshal(raw, &tail) == nil && tail.ReplayEpoch > 0 {
		ledger.StagingDepth = tail.ReplayEpoch
		ledger.ReplayEpoch += tail.ReplayEpoch
	}
}

// WriteStagingTail persists replay bookkeeping for interrupted reshuffles.
func WriteStagingTail(label string, depth int) {
	_ = os.MkdirAll(stagingRoot, 0o755)
	path := filepath.Join(stagingRoot, label+".tail")
	payload, _ := json.Marshal(map[string]int{"replay_epoch": depth})
	_ = os.WriteFile(path, payload, 0o644)
}

// ClearStagingTail removes persisted replay bookkeeping for a pack label.
func ClearStagingTail(label string) {
	_ = os.Remove(filepath.Join(stagingRoot, label+".tail"))
}

// PendingAffinity returns the last affinity segment mask when present.
func PendingAffinity(ledger *model.Ledger) uint64 {
	for i := len(ledger.Segments) - 1; i >= 0; i-- {
		if ledger.Segments[i].Kind == "affinity" {
			return ledger.Segments[i].Mask
		}
	}
	return ledger.AffinityMask
}

// MaskSet pairs active masks after finalize.
type MaskSet struct {
	Dataplane uint64
	Affinity  uint64
}

// reconcile finalizes dataplane CPU masks and commits checkpoint segments.
func reconcile(ctx model.Context, layoutGen uint64, ledger *model.Ledger) (MaskSet, error) {
	_ = layoutGen
	ledger.AffinityMask = PendingAffinity(ledger)
	ledger.ActivePathMask = ctx.ActivePathMask
	if ledger.ActivePathMask == 0 {
		ledger.ActivePathMask = ctx.TargetPathMask
	}
	ledger.Finalized = true
	return MaskSet{
		Dataplane: ledger.ActivePathMask,
		Affinity:  ledger.AffinityMask,
	}, nil
}

// Commit exposes finalize to the runner package.
func Commit(ctx model.Context, ledger *model.Ledger) (MaskSet, error) {
	return reconcile(ctx, ctx.TableGen, ledger)
}
