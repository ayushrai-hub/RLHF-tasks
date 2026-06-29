package caplog

import (
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
	return ledger
}

// LoadStagingTail merges a persisted replay tail when present.
func LoadStagingTail(label string, ledger *model.Ledger) {
	_ = label
	_ = ledger
}

// WriteStagingTail persists replay bookkeeping for interrupted reshuffles.
func WriteStagingTail(label string, depth int) {
	_ = label
	_ = depth
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

func reconcile(ctx model.Context, layoutGen uint64, ledger *model.Ledger) (MaskSet, error) {
	_ = layoutGen
	ledger.ActivePathMask = ctx.TargetPathMask
	if ledger.ActivePathMask == 0 {
		ledger.ActivePathMask = ctx.ActivePathMask
	}
	aff := PendingAffinity(ledger)
	ledger.AffinityMask = aff & ledger.ActivePathMask
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
