package phaseconv

import "nfrd.local/nfrd/model"

func Eligible(rec model.Record, ctx model.Context) bool {
	return rec.RunID == ctx.RunID && rec.Phase == ctx.Phase
}
