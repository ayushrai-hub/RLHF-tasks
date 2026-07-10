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
	// Implement both flood and low intervals using calibrated thresholds at each sample.
	// Extremes are chosen from sampled points only, with earliest-sample tie breaks.
	return []AlertEvent{}
}

func BuildTurns(m model.Model, gauge model.Gauge, rows []SampleRow) []TurnEvent {
	// Interior turning points use the configured delta and the already calibrated levels.
	return []TurnEvent{}
}
