package report

type Sample struct {
	GaugeID string `json:"gauge_id"`
	TimeMin int    `json:"time_min"`
	LevelM  string `json:"level_m"`
}

type Alert struct {
	GaugeID        string `json:"gauge_id"`
	Kind           string `json:"kind"`
	StartMin       int    `json:"start_min"`
	EndMin         int    `json:"end_min"`
	ExtremeTimeMin int    `json:"extreme_time_min"`
	ExtremeLevelM  string `json:"extreme_level_m"`
}

type Turn struct {
	GaugeID string `json:"gauge_id"`
	Kind    string `json:"kind"`
	TimeMin int    `json:"time_min"`
	LevelM  string `json:"level_m"`
}

type Window struct {
	GaugeID             string `json:"gauge_id"`
	Segment             string `json:"segment"`
	StartMin            int    `json:"start_min"`
	EndMin              int    `json:"end_min"`
	MinClearanceM       string `json:"min_clearance_m"`
	MaxAbsSlopeMPerHour string `json:"max_abs_slope_m_per_hour"`
	TargetErrorM        string `json:"target_error_m"`
}

type RoutePlan struct {
	RouteID              string   `json:"route_id"`
	Segments             []string `json:"segments"`
	Windows              []Window `json:"windows"`
	LayoversMin          []int    `json:"layovers_min"`
	TotalPriority        int      `json:"total_priority"`
	TotalDurationMin     int      `json:"total_duration_min"`
	TotalTargetErrorM    string   `json:"total_target_error_m"`
	TotalHandoffPenaltyM string   `json:"total_handoff_penalty_m"`
	MaxAbsSlopeMPerHour  string   `json:"max_abs_slope_m_per_hour"`
}

type Summary struct {
	GaugeCount          int `json:"gauge_count"`
	SampleCount         int `json:"sample_count"`
	FloodAlerts         int `json:"flood_alerts"`
	LowAlerts           int `json:"low_alerts"`
	TurnCount           int `json:"turn_count"`
	WindowCount         int `json:"window_count"`
	SelectedWindowCount int `json:"selected_window_count"`
	RoutePlanCount      int `json:"route_plan_count"`
}

type Document struct {
	Samples         []Sample    `json:"samples"`
	Alerts          []Alert     `json:"alerts"`
	Turns           []Turn      `json:"turns"`
	Windows         []Window    `json:"windows"`
	SelectedWindows []Window    `json:"selected_windows"`
	RoutePlans      []RoutePlan `json:"route_plans"`
	Summary         Summary     `json:"summary"`
}
