package window

// Coalesce reports whether delta_ms (event_ack_ts - anchor_ack_ts) falls inside
// the coalesce window.
func Coalesce(deltaMs, coalesceMs int64) bool {
	return deltaMs >= 0 && deltaMs < coalesceMs
}

// Reorder reports whether delta_ms falls inside the reorder window.
func Reorder(deltaMs, coalesceMs, reorderMs int64) bool {
	return deltaMs >= coalesceMs && deltaMs <= reorderMs
}

// UtcDay returns the integer UTC day-of-epoch derived from milliseconds.
func UtcDay(tsMs int64) int64 {
	return tsMs / 86400000
}
