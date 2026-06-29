package retain

import (
	"pathfb/caplog"
	"pathfb/model"
)

// Merge applies retain snapshots into active mask sets after finalize.
func Merge(ctx model.Context, ms *caplog.MaskSet) {
	if ctx.RetainSeq <= 0 {
		ms.Affinity = ms.Affinity & ms.Dataplane
		return
	}
	shift := uint(ctx.RetainSeq % 8)
	ms.Affinity = (ctx.StrandedPathMask >> shift) & ms.Dataplane
}
