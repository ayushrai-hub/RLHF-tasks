package chrono

import "time"

// ClipMs normalizes durations to whole milliseconds.
func ClipMs(d time.Duration) int64 {
	return d.Milliseconds()
}

// WindowAnchor selects the anchor coordinate compared against the expanded window.
func WindowAnchor(anchorMs, notBeforeMs, notAfterMs int64) int64 {
	return anchorMs
}
