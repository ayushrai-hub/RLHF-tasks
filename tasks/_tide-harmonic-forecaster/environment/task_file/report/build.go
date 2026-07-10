package report

import (
	"fmt"

	"tideharmonic/forecast"
	"tideharmonic/model"
	"tideharmonic/planner"
)

func Build(input model.Input, rowsByGauge map[string][]forecast.SampleRow, routes *planner.RouteBuilder) Document {
	doc := Document{
		Samples:         []Sample{},
		Alerts:          []Alert{},
		Turns:           []Turn{},
		Windows:         []Window{},
		SelectedWindows: []Window{},
		RoutePlans:      []RoutePlan{},
	}

	priority := map[string]int{}
	var internalWindows []planner.Window
	for _, gauge := range input.Gauges {
		priority[gauge.ID] = gauge.Priority
		rows := rowsByGauge[gauge.ID]
		for _, row := range rows {
			doc.Samples = append(doc.Samples, Sample{GaugeID: row.GaugeID, TimeMin: row.TimeMin, LevelM: fmt6(row.Level)})
		}
		for _, alert := range forecast.BuildAlerts(input.Model, gauge, rows) {
			doc.Alerts = append(doc.Alerts, Alert{
				GaugeID: alert.GaugeID, Kind: alert.Kind, StartMin: alert.StartMin, EndMin: alert.EndMin,
				ExtremeTimeMin: alert.ExtremeTimeMin, ExtremeLevelM: fmt6(alert.ExtremeLevel),
			})
		}
		for _, turn := range forecast.BuildTurns(input.Model, gauge, rows) {
			doc.Turns = append(doc.Turns, Turn{GaugeID: turn.GaugeID, Kind: turn.Kind, TimeMin: turn.TimeMin, LevelM: fmt6(turn.Level)})
		}
		internalWindows = append(internalWindows, routes.BuildWindows(input.Model, gauge, rows)...)
	}

	for _, window := range internalWindows {
		doc.Windows = append(doc.Windows, publishWindow(window))
	}
	for _, window := range routes.SelectWindows(internalWindows, priority) {
		doc.SelectedWindows = append(doc.SelectedWindows, publishWindow(window))
	}
	for _, plan := range routes.BuildRoutePlans(input.Model, input.Model.Routes, internalWindows, priority) {
		doc.RoutePlans = append(doc.RoutePlans, publishRoutePlan(plan))
	}

	sortDocument(&doc)
	doc.Summary = summarize(input, doc)
	return doc
}

func publishWindow(window planner.Window) Window {
	return Window{
		GaugeID: window.GaugeID, Segment: window.Segment, StartMin: window.StartMin, EndMin: window.EndMin,
		MinClearanceM: fmt6(window.MinClearance), MaxAbsSlopeMPerHour: fmt6(window.MaxAbsSlope), TargetErrorM: fmt6(window.TargetError),
	}
}

func publishRoutePlan(plan planner.RoutePlan) RoutePlan {
	windows := []Window{}
	for _, window := range plan.Windows {
		windows = append(windows, publishWindow(window))
	}
	layovers := []int{}
	layovers = append(layovers, plan.LayoversMin...)
	return RoutePlan{
		RouteID: plan.RouteID, Segments: append([]string(nil), plan.Segments...), Windows: windows, LayoversMin: layovers,
		TotalPriority: plan.TotalPriority, TotalDurationMin: plan.TotalDurationMin,
		TotalTargetErrorM: fmt6(plan.TotalTargetError), TotalHandoffPenaltyM: fmt6(plan.TotalHandoffPenalty), MaxAbsSlopeMPerHour: fmt6(plan.MaxAbsSlope),
	}
}

func summarize(input model.Input, doc Document) Summary {
	summary := Summary{
		GaugeCount: len(input.Gauges), SampleCount: len(doc.Samples), TurnCount: len(doc.Turns),
		WindowCount: len(doc.Windows), SelectedWindowCount: len(doc.SelectedWindows), RoutePlanCount: len(doc.RoutePlans),
	}
	for _, alert := range doc.Alerts {
		if alert.Kind == "flood" {
			summary.FloodAlerts++
		}
		if alert.Kind == "low" {
			summary.LowAlerts++
		}
	}
	return summary
}

func fmt6(value float64) string {
	return fmt.Sprintf("%.6f", value)
}
