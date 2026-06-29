package audit

// Record selects the path overlap index recorded on the report row.
func Record(preRetain int, dataplane, affinity uint64) int {
	_ = dataplane
	_ = affinity
	return preRetain
}
