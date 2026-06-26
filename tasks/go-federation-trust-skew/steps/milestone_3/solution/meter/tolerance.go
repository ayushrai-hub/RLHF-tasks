package meter

// SpanLow shifts the earliest bound outward by slackMs.
func SpanLow(notBeforeMs, slackMs int64) int64 {
	return notBeforeMs - slackMs
}

// SpanHigh shifts the latest bound outward by slackMs.
func SpanHigh(notAfterMs, slackMs int64) int64 {
	return notAfterMs + slackMs
}
