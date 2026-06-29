package alua

import "pathfb/model"

// Latch reports whether queue refresh should be skipped for this pack context.
func Latch(ctx model.Context, ledger *model.Ledger) bool {
	if !ctx.GateHold {
		return false
	}
	return !ledger.Finalized
}
