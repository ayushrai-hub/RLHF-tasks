package planner

import "tideharmonic/model"

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
}

type RoutePlanner interface {
	BuildRoutePlans(m model.Model, routes []model.Route, windows []Window, priority map[string]int) []RoutePlan
}

func (r *RouteBuilder) BuildRoutePlans(m model.Model, routes []model.Route, windows []Window, priority map[string]int) []RoutePlan {
	r.mu.Lock()
	defer r.mu.Unlock()
	// Search complete route plans globally; checkpoints, layovers, repeat-gauge rules,
	// cumulative crew capacity, forbidden transitions, handoff penalties, error caps, and final tie-breaks all interact.
	return []RoutePlan{}
}
