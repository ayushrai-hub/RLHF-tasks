package window

// Coalesce reports whether delta_ms (event_ack_ts - anchor_ack_ts) falls inside
// the LEFT-INCLUSIVE, RIGHT-INCLUSIVE coalesce window [0, coalesce_ms].
// An event exactly at delta == coalesce_ms IS coalesced.
func Coalesce(deltaMs, coalesceMs int64) bool {
	return deltaMs >= 0 && deltaMs <= coalesceMs
}

// Reorder reports whether delta_ms falls inside the LEFT-EXCLUSIVE, RIGHT-INCLUSIVE
// reorder window (coalesce_ms, reorder_ms]. Adjacent to Coalesce with opposite
// boundary inclusivity on the shared left edge so the two windows are disjoint and
// cover the same boundary unambiguously.
func Reorder(deltaMs, coalesceMs, reorderMs int64) bool {
	return deltaMs > coalesceMs && deltaMs <= reorderMs
}

// UtcDay returns the integer UTC day-of-epoch derived from milliseconds.
func UtcDay(tsMs int64) int64 {
	return tsMs / 86400000
}
