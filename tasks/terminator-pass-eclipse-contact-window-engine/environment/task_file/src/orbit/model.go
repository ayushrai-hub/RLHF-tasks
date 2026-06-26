package orbit

import "errors"

type Elements struct {
	SemiMajorAxisM float64 `json:"semi_major_axis_m"`
	Eccentricity   float64 `json:"eccentricity"`
	InclinationDeg float64 `json:"inclination_deg"`
	RaanDeg        float64 `json:"raan_deg"`
	ArgPerigeeDeg  float64 `json:"arg_perigee_deg"`
	MeanAnomalyDeg float64 `json:"mean_anomaly_deg"`
}

type Station struct {
	ID              string  `json:"id"`
	LatitudeDeg     float64 `json:"latitude_deg"`
	LongitudeDeg    float64 `json:"longitude_deg"`
	AltitudeM       float64 `json:"altitude_m"`
	MinElevationDeg float64 `json:"min_elevation_deg"`
}

type Request struct {
	CaseID             string    `json:"case_id"`
	MuM3S2             float64   `json:"mu_m3_s2"`
	EarthRadiusM       float64   `json:"earth_radius_m"`
	EarthRotationRadS  float64   `json:"earth_rotation_rad_s"`
	Gmst0Deg           float64   `json:"gmst0_deg"`
	CarrierFrequencyHz float64   `json:"carrier_frequency_hz"`
	SunVectorECI       []float64 `json:"sun_vector_eci"`
	RequireSunlit      bool      `json:"require_sunlit"`
	StartTimeS         float64   `json:"start_time_s"`
	DurationS          float64   `json:"duration_s"`
	StepS              float64   `json:"step_s"`
	RootIterations     int       `json:"root_iterations"`
	MaxIterations      int       `json:"max_iterations"`
	Elements           Elements  `json:"elements"`
	Stations           []Station `json:"stations"`
}

type Sample struct {
	TimeS        float64 `json:"time_s"`
	RangeM      float64 `json:"range_m"`
	ElevationDeg float64 `json:"elevation_deg"`
	AzimuthDeg   float64 `json:"azimuth_deg"`
	RangeRateMS  float64 `json:"range_rate_m_s"`
	DopplerHz    float64 `json:"doppler_hz"`
	Sunlit        bool    `json:"sunlit"`
}

type Contact struct {
	StationID       string   `json:"station_id"`
	StartTimeS      float64  `json:"start_time_s"`
	EndTimeS        float64  `json:"end_time_s"`
	DurationS       float64  `json:"duration_s"`
	MaxElevationDeg float64  `json:"max_elevation_deg"`
	MaxElevationTimeS float64 `json:"max_elevation_time_s"`
	MinRangeM       float64  `json:"min_range_m"`
	Samples          []Sample `json:"samples"`
}

type Sensitivity struct {
	Parameter              string  `json:"parameter"`
	DTotalContactSecondsDX float64 `json:"d_total_contact_seconds_d_x"`
}

type EclipseInterval struct {
	StartTimeS float64 `json:"start_time_s"`
	EndTimeS   float64 `json:"end_time_s"`
	DurationS  float64 `json:"duration_s"`
}

type TerminatorEvent struct {
	TimeS        float64  `json:"time_s"`
	Kind         string   `json:"kind"`
	ShadowMargin float64  `json:"shadow_margin_m"`
	VisibleStations []string `json:"visible_stations"`
}

type Response struct {
	CaseID              string        `json:"case_id"`
	TotalContacts       int           `json:"total_contacts"`
	TotalContactSeconds float64       `json:"total_contact_seconds"`
	TotalEclipseSeconds float64       `json:"total_eclipse_seconds"`
	Contacts            []Contact     `json:"contacts"`
	EclipseIntervals    []EclipseInterval `json:"eclipse_intervals"`
	TerminatorEvents    []TerminatorEvent `json:"terminator_events"`
	Sensitivities        []Sensitivity `json:"sensitivities"`
}

func Solve(req Request) (Response, error) {
	return Response{}, errors.New("orbital contact solver is not implemented")
}
