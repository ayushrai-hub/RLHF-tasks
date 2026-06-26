package chrono

import (
	"time"

	"fedenv/meter"
)

// WindowOpen reports whether anchorMs lies within the validity window expanded by slack.
func WindowOpen(anchorMs, notBeforeMs, notAfterMs int64, slack time.Duration) bool {
	low, high := expandWindow(notBeforeMs, notAfterMs, slack)
	if anchorMs < low {
		return false
	}
	if anchorMs > high {
		return false
	}
	return true
}

func expandWindow(notBeforeMs, notAfterMs int64, slack time.Duration) (int64, int64) {
	s := slack.Milliseconds()
	return meter.SpanLow(notBeforeMs, s), meter.SpanHigh(notAfterMs, s)
}
