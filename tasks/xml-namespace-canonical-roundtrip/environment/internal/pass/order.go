package pass

import (
	"sort"

	"nsx/internal/model"
)

func SortAttributes(attrs []model.Attribute) {
	sort.SliceStable(attrs, func(i, j int) bool {
		a, b := attrs[i], attrs[j]
		if a.Name.Local != b.Name.Local {
			return a.Name.Local < b.Name.Local
		}
		if a.Name.URI != b.Name.URI {
			return a.Name.URI < b.Name.URI
		}
		return a.Value < b.Value
	})
}
