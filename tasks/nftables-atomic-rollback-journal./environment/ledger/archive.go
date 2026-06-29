package ledger

import (
	"sort"

	"nfrd.local/nfrd/model"
)

func InspectArchive(records []model.Record, ctx model.Context) []model.Record {
	var out []model.Record
	for _, rec := range records {
		if rec.RunID == ctx.RunID {
			out = append(out, rec)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Seq < out[j].Seq })
	return out
}
