package retain

import (
	"pathfb/model"
	"pathfb/caplog"
)

// Merge applies retain snapshots into active mask sets after finalize.
func Merge(ctx model.Context, ms *caplog.MaskSet) {
	if ctx.RetainSeq <= 0 {
		return
	}
	ms.Affinity = ctx.StrandedPathMask
}
