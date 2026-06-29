package audit

import "pathfb/spread"

// Record selects the path overlap index recorded on the report row.
func Record(preRetain int, dataplane, affinity uint64) int {
	_ = preRetain
	return spread.SpreadIndex(dataplane, affinity)
}
