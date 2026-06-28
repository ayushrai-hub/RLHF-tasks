package ordering

import (
	"sort"
	"logrecover/pkg/api"
)

func WallClockSort(events []api.Event, wallMS []int64) {
	if len(wallMS) != len(events) {
		return
	}
	sort.Slice(events, func(i, j int) bool {
		return wallMS[i] < wallMS[j]
	})
}
