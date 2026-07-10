package planner

import (
	"sync"

	"tideharmonic/forecast"
	"tideharmonic/model"
)

type Window struct {
	GaugeID      string
	Segment      string
	StartMin     int
	EndMin       int
	MinClearance float64
	MaxAbsSlope  float64
	TargetError  float64
}

type WindowPlanner interface {
	BuildWindows(m model.Model, gauge model.Gauge, rows []forecast.SampleRow) []Window
	SelectWindows(windows []Window, priority map[string]int) []Window
}

type RouteBuilder struct {
	mu sync.Mutex
}

func (r *RouteBuilder) BuildWindows(m model.Model, gauge model.Gauge, rows []forecast.SampleRow) []Window {
	r.mu.Lock()
	defer r.mu.Unlock()
	// Build maximal safe runs after applying closures, blackouts, calibrated thresholds,
	// calibrated draft clearance, strict threshold bounds, slope limits, and minimum duration.
	// Report clearance and target error exactly as defined in instruction.md.
	return []Window{}
}

func (r *RouteBuilder) SelectWindows(windows []Window, priority map[string]int) []Window {
	r.mu.Lock()
	defer r.mu.Unlock()
	// Select one window per segment using the full operations tie-break chain in instruction.md.
	return []Window{}
}
