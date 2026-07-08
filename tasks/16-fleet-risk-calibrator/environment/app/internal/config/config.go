package config

type Model struct {
	ModelID          string                        `json:"model_id"`
	FeatureParams    FeatureParams                 `json:"feature_params"`
	Heads            map[string]ModelHead          `json:"heads"`
	BlendByAssetType map[string]map[string]float64 `json:"blend_by_asset_type"`
	PostCalibration  PostCalibration               `json:"post_calibration"`
	AssetTypes       map[string]AssetType          `json:"asset_types"`
}

type FeatureParams struct {
	TrendLookbackHours    float64 `json:"trend_lookback_hours"`
	TempEWMAHalfLifeHours float64 `json:"temp_ewma_half_life_hours"`
	HistoryLookbackDays   float64 `json:"history_lookback_days"`
	HistoryHalfLifeDays   float64 `json:"history_half_life_days"`
}

type ModelHead struct {
	Intercept   float64            `json:"intercept"`
	Weights     map[string]float64 `json:"weights"`
	Calibration []CalibrationKnot  `json:"calibration"`
}

type CalibrationKnot struct {
	Raw        float64 `json:"raw"`
	Calibrated float64 `json:"calibrated"`
}

type PostCalibration struct {
	BlendWeight float64                            `json:"blend_weight"`
	Groups      map[string][]CalibrationObservation `json:"groups"`
}

type CalibrationObservation struct {
	Raw    float64 `json:"raw"`
	Label  float64 `json:"label"`
	Weight float64 `json:"weight"`
}

type AssetType struct {
	TempLimitC         float64 `json:"temp_limit_c"`
	MaxVibrationMMS    float64 `json:"max_vibration_mm_s"`
	NominalPressureKPA float64 `json:"nominal_pressure_kpa"`
	CurrentMeanA       float64 `json:"current_mean_a"`
	CurrentStdA        float64 `json:"current_std_a"`
	ImputeTempC        float64 `json:"impute_temp_c"`
}

type Policy struct {
	PolicyID          string     `json:"policy_id"`
	ReportGeneratedAt string     `json:"report_generated_at"`
	Thresholds        Thresholds `json:"thresholds"`
	DueHours          DueHours   `json:"due_hours"`
	Optimizer         Optimizer  `json:"optimizer"`
}

type Thresholds struct {
	Dispatch           float64 `json:"dispatch"`
	Inspect            float64 `json:"inspect"`
	Watch              float64 `json:"watch"`
	UrgentInspectFloor float64 `json:"urgent_inspect_floor"`
}

type DueHours struct {
	Dispatch int `json:"dispatch"`
	Inspect  int `json:"inspect"`
	Monitor  int `json:"monitor"`
}

type Optimizer struct {
	RiskEffect     map[string]float64                      `json:"risk_effect"`
	DowntimeEffect map[string]float64                      `json:"downtime_effect"`
	ActionCost     map[string]float64                      `json:"action_cost"`
	MinimumRisk    map[string]float64                      `json:"minimum_risk"`
	SiteRegion     map[string]string                       `json:"site_region"`
	RegionalLimits map[string]RegionalLimit                `json:"regional_limits"`
	ActionHours    map[string]map[string]float64            `json:"action_hours"`
	ActionParts    map[string]map[string]map[string]int     `json:"action_parts"`
	PartsInventory []PartInventory                          `json:"parts_inventory"`
	CrewRoster     []Crew                                    `json:"crew_roster"`
	BreakHours     float64                                   `json:"break_hours"`
	PartTransfer   map[string]map[string]map[string]float64 `json:"part_transfer_hours"`
	TravelHours    map[string]map[string]map[string]float64 `json:"travel_hours"`
	PriorityBonus  map[string]map[string]float64            `json:"priority_bonus"`
}

type RegionalLimit struct {
	DispatchSlots int     `json:"dispatch_slots"`
	InspectSlots  int     `json:"inspect_slots"`
	CrewHours     float64 `json:"crew_hours"`
}

type PartInventory struct {
	Site       string `json:"site"`
	PartID     string `json:"part_id"`
	OnHand     int    `json:"on_hand"`
	ReserveMin int    `json:"reserve_min"`
}

type Crew struct {
	CrewID             string  `json:"crew_id"`
	Region             string  `json:"region"`
	HomeSite           string  `json:"home_site"`
	ShiftStart         string  `json:"shift_start"`
	ShiftEnd           string  `json:"shift_end"`
	MaxContinuousHours float64 `json:"max_continuous_hours"`
}
