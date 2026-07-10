#!/bin/bash
set -euo pipefail

cat > /app/forecast/series.go <<'GO'
package forecast

import (
	"math"

	"tideharmonic/model"
)

type SeriesBuilder interface {
	BuildSeries(input model.Input) map[string][]SampleRow
}

type Engine struct{}

type SampleRow struct {
	GaugeID string
	TimeMin int
	Level   float64
}

func (Engine) BuildSeries(input model.Input) map[string][]SampleRow {
	rowsByGauge := map[string][]SampleRow{}
	for _, gauge := range input.Gauges {
		var rows []SampleRow
		for t := input.Model.StartMin; t <= input.Model.EndMin; t += input.Model.StepMin {
			rows = append(rows, SampleRow{GaugeID: gauge.ID, TimeMin: t, Level: LevelAt(input.Model, gauge, t)})
		}
		rowsByGauge[gauge.ID] = rows
	}
	return rowsByGauge
}

func LevelAt(m model.Model, gauge model.Gauge, t int) float64 {
	levelShift, _, _, _ := model.CalibrationShifts(m, gauge, t)
	level := m.DatumM + gauge.OffsetM + gauge.DriftMPerDay*(float64(t-m.StartMin)/1440.0) + levelShift
	for _, c := range m.Constituents {
		angle := c.SpeedDegPerHour*(float64(t+gauge.PhaseLagMin-c.EpochMin)/60.0) + c.PhaseDeg
		level += gauge.Scale * c.AmplitudeM * c.NodalFactor * math.Cos(angle*math.Pi/180.0)
	}
	return level
}
GO

cat > /app/forecast/events.go <<'GO'
package forecast

import "tideharmonic/model"

type AlertEvent struct {
	GaugeID        string
	Kind           string
	StartMin       int
	EndMin         int
	ExtremeTimeMin int
	ExtremeLevel   float64
}

type TurnEvent struct {
	GaugeID string
	Kind    string
	TimeMin int
	Level   float64
}

func BuildAlerts(m model.Model, gauge model.Gauge, rows []SampleRow) []AlertEvent {
	alerts := []AlertEvent{}
	alerts = append(alerts, buildAlerts(m, gauge, rows, "flood")...)
	alerts = append(alerts, buildAlerts(m, gauge, rows, "low")...)
	return alerts
}

func buildAlerts(m model.Model, gauge model.Gauge, rows []SampleRow, kind string) []AlertEvent {
	active := func(row SampleRow) bool {
		flood, low := model.Thresholds(m, gauge, row.TimeMin)
		if kind == "flood" {
			return row.Level >= flood
		}
		return row.Level <= low
	}
	alerts := []AlertEvent{}
	for i := 0; i < len(rows); {
		if !active(rows[i]) {
			i++
			continue
		}
		start := i
		best := i
		for i+1 < len(rows) && active(rows[i+1]) {
			i++
			if kind == "flood" {
				if rows[i].Level > rows[best].Level {
					best = i
				}
			} else if rows[i].Level < rows[best].Level {
				best = i
			}
		}
		alerts = append(alerts, AlertEvent{
			GaugeID: gauge.ID, Kind: kind, StartMin: rows[start].TimeMin, EndMin: rows[i].TimeMin,
			ExtremeTimeMin: rows[best].TimeMin, ExtremeLevel: rows[best].Level,
		})
		i++
	}
	return alerts
}

func BuildTurns(m model.Model, gauge model.Gauge, rows []SampleRow) []TurnEvent {
	turns := []TurnEvent{}
	for i := 1; i < len(rows)-1; i++ {
		prev := rows[i-1].Level
		level := rows[i].Level
		next := rows[i+1].Level
		if level-prev >= m.TurnMinDeltaM && level-next >= m.TurnMinDeltaM {
			turns = append(turns, TurnEvent{GaugeID: gauge.ID, Kind: "high", TimeMin: rows[i].TimeMin, Level: level})
		}
		if prev-level >= m.TurnMinDeltaM && next-level >= m.TurnMinDeltaM {
			turns = append(turns, TurnEvent{GaugeID: gauge.ID, Kind: "low", TimeMin: rows[i].TimeMin, Level: level})
		}
	}
	return turns
}
GO

cat > /app/planner/windows.go <<'GO'
package planner

import (
	"math"
	"sort"
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
	CrewCapacity int
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

	windows := []Window{}
	for i := 0; i < len(rows); {
		if !sampleSafe(m, gauge, rows[i]) {
			i++
			continue
		}
		run := []forecast.SampleRow{rows[i]}
		i++
		for i < len(rows) && sampleSafe(m, gauge, rows[i]) {
			if math.Abs(slopePerHour(run[len(run)-1], rows[i])) > m.Operations.MaxSlopeMPerHour {
				break
			}
			run = append(run, rows[i])
			i++
		}
		if run[len(run)-1].TimeMin-run[0].TimeMin >= m.Operations.MinWindowMin {
			windows = append(windows, makeWindow(m, gauge, run))
		}
	}
	return windows
}

func sampleSafe(m model.Model, gauge model.Gauge, row forecast.SampleRow) bool {
	flood, low := model.Thresholds(m, gauge, row.TimeMin)
	_, _, _, draftShift := model.CalibrationShifts(m, gauge, row.TimeMin)
	draft := gauge.DraftM + draftShift
	return row.Level < flood &&
		row.Level > low &&
		!closedAt(m, gauge, row.TimeMin) &&
		!blackedOutAt(m, gauge, row.TimeMin) &&
		row.Level >= draft+m.Operations.MinUnderKeelM &&
		row.Level <= flood-m.Operations.FloodBufferM
}

func closedAt(m model.Model, gauge model.Gauge, timeMin int) bool {
	for _, closure := range m.Closures {
		if closure.GaugeID == gauge.ID && closure.StartMin <= timeMin && timeMin <= closure.EndMin {
			return true
		}
	}
	return false
}

func blackedOutAt(m model.Model, gauge model.Gauge, timeMin int) bool {
	for _, blackout := range m.Blackouts {
		if blackout.Segment == gauge.Segment && blackout.StartMin <= timeMin && timeMin <= blackout.EndMin {
			return true
		}
	}
	return false
}

func makeWindow(m model.Model, gauge model.Gauge, run []forecast.SampleRow) Window {
	minClearance := math.Inf(1)
	maxSlope := 0.0
	targetError := 0.0
	for i, row := range run {
		_, _, _, draftShift := model.CalibrationShifts(m, gauge, row.TimeMin)
		clearance := row.Level - gauge.DraftM - draftShift
		if clearance < minClearance {
			minClearance = clearance
		}
		targetError += math.Abs(row.Level - m.Operations.TargetLevelM)
		if i+1 < len(run) {
			slope := math.Abs(slopePerHour(row, run[i+1]))
			if slope > maxSlope {
				maxSlope = slope
			}
		}
	}
	return Window{
		GaugeID: gauge.ID, Segment: gauge.Segment, StartMin: run[0].TimeMin, EndMin: run[len(run)-1].TimeMin,
		MinClearance: minClearance, MaxAbsSlope: maxSlope, TargetError: targetError / float64(len(run)), CrewCapacity: gauge.CrewCapacity,
	}
}

func slopePerHour(a, b forecast.SampleRow) float64 {
	return (b.Level - a.Level) / (float64(b.TimeMin-a.TimeMin) / 60.0)
}

func (r *RouteBuilder) SelectWindows(windows []Window, priority map[string]int) []Window {
	r.mu.Lock()
	defer r.mu.Unlock()

	best := map[string]Window{}
	for _, window := range windows {
		current, ok := best[window.Segment]
		if !ok || betterWindow(window, current, priority) {
			best[window.Segment] = window
		}
	}
	segments := []string{}
	for segment := range best {
		segments = append(segments, segment)
	}
	sort.Strings(segments)
	selected := []Window{}
	for _, segment := range segments {
		selected = append(selected, best[segment])
	}
	return selected
}

func betterWindow(a, b Window, priority map[string]int) bool {
	if priority[a.GaugeID] != priority[b.GaugeID] {
		return priority[a.GaugeID] > priority[b.GaugeID]
	}
	if a.TargetError != b.TargetError {
		return a.TargetError < b.TargetError
	}
	aDuration := a.EndMin - a.StartMin
	bDuration := b.EndMin - b.StartMin
	if aDuration != bDuration {
		return aDuration > bDuration
	}
	if a.MaxAbsSlope != b.MaxAbsSlope {
		return a.MaxAbsSlope < b.MaxAbsSlope
	}
	if a.StartMin != b.StartMin {
		return a.StartMin < b.StartMin
	}
	return a.GaugeID < b.GaugeID
}
GO

cat > /app/planner/routes.go <<'GO'
package planner

import (
	"sort"
	"strings"

	"tideharmonic/model"
)

type RoutePlan struct {
	RouteID             string
	Segments            []string
	Windows             []Window
	LayoversMin         []int
	TotalPriority       int
	TotalDurationMin    int
	TotalTargetError    float64
	TotalHandoffPenalty float64
	MaxAbsSlope         float64
	firstStartMin       int
	gaugeIDs            string
}

type RoutePlanner interface {
	BuildRoutePlans(m model.Model, routes []model.Route, windows []Window, priority map[string]int) []RoutePlan
}

func (r *RouteBuilder) BuildRoutePlans(m model.Model, routes []model.Route, windows []Window, priority map[string]int) []RoutePlan {
	r.mu.Lock()
	defer r.mu.Unlock()

	plans := []RoutePlan{}
	for _, route := range routes {
		if plan, ok := bestRoutePlan(m, route, windows, priority); ok {
			plans = append(plans, plan)
		}
	}
	sort.Slice(plans, func(i, j int) bool {
		return plans[i].RouteID < plans[j].RouteID
	})
	return plans
}

func bestRoutePlan(m model.Model, route model.Route, windows []Window, priority map[string]int) (RoutePlan, bool) {
	bySegment := map[string][]Window{}
	for _, window := range windows {
		bySegment[window.Segment] = append(bySegment[window.Segment], window)
	}
	for segment := range bySegment {
		sort.Slice(bySegment[segment], func(i, j int) bool {
			a := bySegment[segment][i]
			b := bySegment[segment][j]
			if a.StartMin != b.StartMin {
				return a.StartMin < b.StartMin
			}
			if a.EndMin != b.EndMin {
				return a.EndMin < b.EndMin
			}
			return a.GaugeID < b.GaugeID
		})
	}

	var best RoutePlan
	found := false
	var visit func(int, []Window)
	visit = func(index int, plan []Window) {
		if index == len(route.Segments) {
			if !routeCapacityAllows(m, route, plan) {
				return
			}
			candidate := makeRoutePlan(route, plan, priority, m.Operations)
			if m.Operations.RouteMaxTotalTargetErrorM != nil && candidate.TotalTargetError > *m.Operations.RouteMaxTotalTargetErrorM {
				return
			}
			if !found || betterRoutePlan(candidate, best) {
				best = candidate
				found = true
			}
			return
		}
		for _, window := range bySegment[route.Segments[index]] {
			if !checkpointAllows(route, index, window) {
				continue
			}
			if m.Operations.RouteNoRepeatGauge && hasGauge(plan, window.GaugeID) {
				continue
			}
			if len(plan) > 0 {
				if !transitionAllowed(route, plan[len(plan)-1], window) {
					continue
				}
				gap := window.StartMin - plan[len(plan)-1].EndMin
				if gap < m.Operations.RouteMinGapMin || gap > m.Operations.RouteMaxLayoverMin {
					continue
				}
			}
			next := append(plan, window)
			visit(index+1, next)
		}
	}
	visit(0, []Window{})
	return best, found
}

func routeCapacityAllows(m model.Model, route model.Route, windows []Window) bool {
	used := map[string]int{}
	for i, window := range windows {
		cost := segmentCrewCost(m, route.Segments[i])
		if cost == 0 {
			continue
		}
		used[window.GaugeID] += cost
		if used[window.GaugeID] > window.CrewCapacity {
			return false
		}
	}
	return true
}

func segmentCrewCost(m model.Model, segmentID string) int {
	for _, segment := range m.Segments {
		if segment.ID == segmentID {
			return segment.CrewCost
		}
	}
	return 0
}

func checkpointAllows(route model.Route, index int, window Window) bool {
	for _, checkpoint := range route.Checkpoints {
		if checkpoint.Index != index {
			continue
		}
		if window.StartMin < checkpoint.EarliestStartMin || window.EndMin > checkpoint.LatestEndMin {
			return false
		}
		if checkpoint.RequiredGaugeID != "" && window.GaugeID != checkpoint.RequiredGaugeID {
			return false
		}
	}
	return true
}

func transitionAllowed(route model.Route, previous, current Window) bool {
	for _, transition := range route.ForbiddenTransitions {
		fromMatches := transition.FromGaugeID == "" || previous.GaugeID == transition.FromGaugeID
		toMatches := transition.ToGaugeID == "" || current.GaugeID == transition.ToGaugeID
		if fromMatches && toMatches {
			return false
		}
	}
	return true
}

func hasGauge(windows []Window, gaugeID string) bool {
	for _, window := range windows {
		if window.GaugeID == gaugeID {
			return true
		}
	}
	return false
}

func makeRoutePlan(route model.Route, windows []Window, priority map[string]int, ops model.Operations) RoutePlan {
	copied := append([]Window(nil), windows...)
	plan := RoutePlan{RouteID: route.ID, Segments: append([]string(nil), route.Segments...), Windows: copied, LayoversMin: []int{}}
	ids := []string{}
	for i, window := range copied {
		plan.TotalPriority += priority[window.GaugeID]
		plan.TotalDurationMin += window.EndMin - window.StartMin
		plan.TotalTargetError += window.TargetError
		if i > 0 {
			plan.LayoversMin = append(plan.LayoversMin, window.StartMin-copied[i-1].EndMin)
			if window.GaugeID != copied[i-1].GaugeID {
				plan.TotalHandoffPenalty += handoffPenalty(route, ops)
			}
		}
		if i == 0 || window.MaxAbsSlope > plan.MaxAbsSlope {
			plan.MaxAbsSlope = window.MaxAbsSlope
		}
		if i == 0 {
			plan.firstStartMin = window.StartMin
		}
		ids = append(ids, window.GaugeID)
	}
	plan.gaugeIDs = strings.Join(ids, ",")
	plan.TotalTargetError += plan.TotalHandoffPenalty
	return plan
}

func handoffPenalty(route model.Route, ops model.Operations) float64 {
	if route.HandoffPenaltyM != nil {
		return *route.HandoffPenaltyM
	}
	return ops.RouteHandoffPenaltyM
}

func betterRoutePlan(a, b RoutePlan) bool {
	if a.TotalPriority != b.TotalPriority {
		return a.TotalPriority > b.TotalPriority
	}
	if a.TotalTargetError != b.TotalTargetError {
		return a.TotalTargetError < b.TotalTargetError
	}
	if a.TotalDurationMin != b.TotalDurationMin {
		return a.TotalDurationMin > b.TotalDurationMin
	}
	if a.MaxAbsSlope != b.MaxAbsSlope {
		return a.MaxAbsSlope < b.MaxAbsSlope
	}
	if a.firstStartMin != b.firstStartMin {
		return a.firstStartMin < b.firstStartMin
	}
	return a.gaugeIDs < b.gaugeIDs
}
GO

gofmt -w /app/forecast/series.go /app/forecast/events.go /app/planner/windows.go /app/planner/routes.go
cd /app
go build -o /app/tide-harmonic-forecaster .
/app/tide-harmonic-forecaster
echo "Tide harmonic forecaster completed."
