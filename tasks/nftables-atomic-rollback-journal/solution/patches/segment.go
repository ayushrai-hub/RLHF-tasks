package batch

import (
	"sort"

	"nfrd.local/nfrd/model"
)

func SelectSegments(records []model.Record, ctx model.Context) []model.Record {
	out := make([]model.Record, 0, len(records))
	for _, rec := range records {
		if rec.RunID != ctx.RunID {
			continue
		}
		if rec.Phase != ctx.Phase {
			continue
		}
		out = append(out, rec)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Seq < out[j].Seq })
	return out
}
