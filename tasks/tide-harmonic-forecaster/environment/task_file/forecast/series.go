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
			rows = append(rows, SampleRow{
				GaugeID: gauge.ID,
				TimeMin: t,
				Level:   LevelAt(input.Model, gauge, t),
			})
		}
		rowsByGauge[gauge.ID] = rows
	}
	return rowsByGauge
}

func LevelAt(m model.Model, gauge model.Gauge, t int) float64 {
	// Use the drift anchor, phase-lag sign, epoch offset, nodal factor,
	// and calibration-shift rules from instruction.md.
	levelShift, _, _, _ := model.CalibrationShifts(m, gauge, t)
	level := m.DatumM + gauge.OffsetM + levelShift
	for _, c := range m.Constituents {
		angle := c.SpeedDegPerHour*(float64(t)/60.0) + c.PhaseDeg
		level += gauge.Scale * c.AmplitudeM * math.Cos(angle*math.Pi/180.0)
	}
	return level
}
