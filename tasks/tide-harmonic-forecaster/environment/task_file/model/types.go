package model

type Input struct {
	Model  Model
	Gauges []Gauge
}

type Model struct {
	StartMin          int                `json:"start_min"`
	EndMin            int                `json:"end_min"`
	StepMin           int                `json:"step_min"`
	DatumM            float64            `json:"datum_m"`
	FloodThresholdM   float64            `json:"flood_threshold_m"`
	LowThresholdM     float64            `json:"low_threshold_m"`
	TurnMinDeltaM     float64            `json:"turn_min_delta_m"`
	Constituents      []Constituent      `json:"constituents"`
	Segments          []Segment          `json:"segments"`
	CalibrationEvents []CalibrationEvent `json:"calibration_events"`
	Closures          []Closure          `json:"closures"`
	Blackouts         []Blackout         `json:"blackouts"`
	Operations        Operations         `json:"operations"`
	Routes            []Route            `json:"routes"`
}

type Constituent struct {
	Name            string  `json:"name"`
	AmplitudeM      float64 `json:"amplitude_m"`
	SpeedDegPerHour float64 `json:"speed_deg_per_hour"`
	PhaseDeg        float64 `json:"phase_deg"`
	NodalFactor     float64 `json:"nodal_factor"`
	EpochMin        int     `json:"epoch_min"`
}

type Segment struct {
	ID              string  `json:"id"`
	FloodThresholdM float64 `json:"flood_threshold_m"`
	LowThresholdM   float64 `json:"low_threshold_m"`
	CrewCost        int     `json:"crew_cost"`
}

type CalibrationEvent struct {
	Target                 string  `json:"target"`
	StartMin               int     `json:"start_min"`
	EndMin                 int     `json:"end_min"`
	LevelShiftM            float64 `json:"level_shift_m"`
	FloodThresholdShiftM   float64 `json:"flood_threshold_shift_m"`
	LowThresholdShiftM     float64 `json:"low_threshold_shift_m"`
	DraftShiftM            float64 `json:"draft_shift_m"`
}

type Closure struct {
	GaugeID  string `json:"gauge_id"`
	StartMin int    `json:"start_min"`
	EndMin   int    `json:"end_min"`
}

type Blackout struct {
	Segment  string `json:"segment"`
	StartMin int    `json:"start_min"`
	EndMin   int    `json:"end_min"`
}

type Operations struct {
	MinUnderKeelM              float64  `json:"min_under_keel_m"`
	FloodBufferM               float64  `json:"flood_buffer_m"`
	MaxSlopeMPerHour           float64  `json:"max_slope_m_per_hour"`
	MinWindowMin               int      `json:"min_window_min"`
	TargetLevelM               float64  `json:"target_level_m"`
	RouteHandoffPenaltyM       float64  `json:"route_handoff_penalty_m"`
	RouteMinGapMin             int      `json:"route_min_gap_min"`
	RouteMaxLayoverMin         int      `json:"route_max_layover_min"`
	RouteNoRepeatGauge         bool     `json:"route_no_repeat_gauge"`
	RouteMaxTotalTargetErrorM  *float64 `json:"route_max_total_target_error_m"`
}

type Route struct {
	ID                   string                `json:"id"`
	Segments             []string              `json:"segments"`
	Checkpoints          []Checkpoint          `json:"checkpoints"`
	ForbiddenTransitions []ForbiddenTransition `json:"forbidden_transitions"`
	HandoffPenaltyM      *float64              `json:"handoff_penalty_m"`
}

type ForbiddenTransition struct {
	FromGaugeID string `json:"from_gauge_id"`
	ToGaugeID   string `json:"to_gauge_id"`
}

type Checkpoint struct {
	Index            int    `json:"index"`
	EarliestStartMin int    `json:"earliest_start_min"`
	LatestEndMin     int    `json:"latest_end_min"`
	RequiredGaugeID  string `json:"required_gauge_id"`
}

type Gauge struct {
	ID           string  `json:"id"`
	Segment      string  `json:"segment"`
	OffsetM      float64 `json:"offset_m"`
	Scale        float64 `json:"scale"`
	DriftMPerDay float64 `json:"drift_m_per_day"`
	PhaseLagMin  int     `json:"phase_lag_min"`
	DraftM       float64 `json:"draft_m"`
	Priority     int     `json:"priority"`
	CrewCapacity int     `json:"crew_capacity"`
}

func CalibrationShifts(m Model, gauge Gauge, t int) (float64, float64, float64, float64) {
	var levelShift, floodShift, lowShift, draftShift float64
	for _, event := range m.CalibrationEvents {
		if t < event.StartMin || t > event.EndMin {
			continue
		}
		if event.Target != "*" && event.Target != gauge.ID && event.Target != gauge.Segment {
			continue
		}
		levelShift += event.LevelShiftM
		floodShift += event.FloodThresholdShiftM
		lowShift += event.LowThresholdShiftM
		draftShift += event.DraftShiftM
	}
	return levelShift, floodShift, lowShift, draftShift
}

func Thresholds(m Model, gauge Gauge, t int) (float64, float64) {
	_, floodShift, lowShift, _ := CalibrationShifts(m, gauge, t)
	for _, segment := range m.Segments {
		if segment.ID == gauge.Segment {
			return segment.FloodThresholdM + floodShift, segment.LowThresholdM + lowShift
		}
	}
	return m.FloodThresholdM + floodShift, m.LowThresholdM + lowShift
}
