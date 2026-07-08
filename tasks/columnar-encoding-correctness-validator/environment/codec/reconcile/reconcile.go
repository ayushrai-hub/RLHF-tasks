package reconcile

import "columnarvalidator/codec/types"

// Result mirrors types.SegmentResult for the reconcile package API.
type Result = types.SegmentResult

// ValidateSegment replays encodings, checks integrity rules, and returns per-segment findings.
func ValidateSegment(seg types.Segment) Result {
	panic("reconcile.ValidateSegment not implemented")
}

// BuildReport aggregates per-segment results into the top-level report.
func BuildReport(results []Result) types.Report {
	panic("reconcile.BuildReport not implemented")
}
