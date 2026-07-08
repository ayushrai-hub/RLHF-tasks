package features

import (
	"fmt"
	"math"
	"sort"

	"example.com/fleetrisk/internal/config"
	"example.com/fleetrisk/internal/domain"
)

var Order = []string{
	"temp_over_limit",
	"vibration_ratio",
	"pressure_delta",
	"current_z",
	"runtime_log",
	"urgent_flag",
	"rework_flag",
	"tech_hours_scaled",
	"temp_rise",
	"repeat_repair_rate",
	"severity_memory",
	"vibration_slope",
	"history_decay",
	"leak_flag",
	"heat_flag",
	"pressure_drift",
}

func Extract(call domain.ServiceCall, window domain.SensorWindow, allWindows []domain.SensorWindow, history []domain.HistoryEvent, model config.Model) (map[string]float64, error) {
	assetConfig, ok := model.AssetTypes[call.AssetType]
	if !ok {
		return nil, fmt.Errorf("unknown asset type %s", call.AssetType)
	}
	if assetConfig.MaxVibrationMMS == 0 || assetConfig.NominalPressureKPA == 0 || assetConfig.CurrentStdA == 0 {
		return nil, fmt.Errorf("invalid scaling config for asset type %s", call.AssetType)
	}
	params := model.FeatureParams
	temp := effectiveTemp(window, allWindows, assetConfig, params)
	previous, hasPrevious := previousWindow(window, allWindows)
	previousTemp := assetConfig.ImputeTempC
	if hasPrevious {
		previousTemp = effectiveTemp(previous, allWindows, assetConfig, params)
	}

	urgent := 0.0
	if call.Priority == "urgent" {
		urgent = 1.0
	}
	rework := 0.0
	if call.NotesCode == "REWORK" {
		rework = 1.0
	}
	leak := 0.0
	if call.NotesCode == "LEAK" {
		leak = 1.0
	}
	heat := 0.0
	if call.NotesCode == "HEAT" {
		heat = 1.0
	}

	repeatRepairs := 0
	severityMemory := 0
	historyDecay := 0.0
	for _, event := range history {
		if event.AssetID != call.AssetID || !event.EventTime.Before(call.OpenedAt) {
			continue
		}
		ageDays := call.OpenedAt.Sub(event.EventTime).Hours() / 24
		if event.EventType == "corrective" && ageDays <= 45 {
			repeatRepairs++
		}
		if (event.EventType == "corrective" || event.EventType == "failure") && ageDays <= 90 && event.Severity > severityMemory {
			severityMemory = event.Severity
		}
		if (event.EventType == "corrective" || event.EventType == "failure") && ageDays <= params.HistoryLookbackDays {
			historyDecay += (float64(event.Severity) / 5.0) * math.Pow(0.5, ageDays/params.HistoryHalfLifeDays)
		}
	}
	if repeatRepairs > 3 {
		repeatRepairs = 3
	}

	pressureDrift := 0.0
	if hasPrevious {
		pressureDrift = math.Abs(window.PressureKPA-previous.PressureKPA) / assetConfig.NominalPressureKPA
	}

	values := map[string]float64{
		"temp_over_limit":    math.Max(0, temp-assetConfig.TempLimitC) / 10,
		"vibration_ratio":    math.Min(window.VibrationMMS/assetConfig.MaxVibrationMMS, 3.0),
		"pressure_delta":     math.Abs(window.PressureKPA-assetConfig.NominalPressureKPA) / assetConfig.NominalPressureKPA,
		"current_z":          (window.CurrentA - assetConfig.CurrentMeanA) / assetConfig.CurrentStdA,
		"runtime_log":        math.Log1p(window.RuntimeHours) / 10,
		"urgent_flag":        urgent,
		"rework_flag":        rework,
		"tech_hours_scaled":  call.TechnicianHours / 4,
		"temp_rise":          math.Max(0, temp-previousTemp) / 10,
		"repeat_repair_rate": float64(repeatRepairs) / 3,
		"severity_memory":    float64(severityMemory) / 5,
		"vibration_slope":    vibrationSlope(window, allWindows, assetConfig, params),
		"history_decay":      math.Min(historyDecay, 2.5) / 2.5,
		"leak_flag":          leak,
		"heat_flag":          heat,
		"pressure_drift":     pressureDrift,
	}
	return values, nil
}

func effectiveTemp(window domain.SensorWindow, windows []domain.SensorWindow, assetConfig config.AssetType, params config.FeatureParams) float64 {
	if window.TempC != nil {
		return *window.TempC
	}
	numerator := 0.0
	denominator := 0.0
	for _, candidate := range windows {
		if candidate.AssetID != window.AssetID || candidate.TempC == nil || !candidate.WindowEnd.Before(window.WindowEnd) {
			continue
		}
		ageHours := window.WindowEnd.Sub(candidate.WindowEnd).Hours()
		if ageHours > params.TrendLookbackHours {
			continue
		}
		weight := math.Pow(0.5, ageHours/params.TempEWMAHalfLifeHours)
		numerator += *candidate.TempC * weight
		denominator += weight
	}
	if denominator == 0 {
		return assetConfig.ImputeTempC
	}
	return numerator / denominator
}

func previousWindow(matched domain.SensorWindow, windows []domain.SensorWindow) (domain.SensorWindow, bool) {
	var previous domain.SensorWindow
	found := false
	for _, candidate := range windows {
		if candidate.AssetID != matched.AssetID || !candidate.WindowEnd.Before(matched.WindowEnd) {
			continue
		}
		if !found || candidate.WindowEnd.After(previous.WindowEnd) {
			previous = candidate
			found = true
		}
	}
	return previous, found
}

func vibrationSlope(matched domain.SensorWindow, windows []domain.SensorWindow, assetConfig config.AssetType, params config.FeatureParams) float64 {
	candidates := make([]domain.SensorWindow, 0)
	for _, candidate := range windows {
		if candidate.AssetID != matched.AssetID || candidate.WindowEnd.After(matched.WindowEnd) {
			continue
		}
		if matched.WindowEnd.Sub(candidate.WindowEnd).Hours() > params.TrendLookbackHours {
			continue
		}
		candidates = append(candidates, candidate)
	}
	if len(candidates) < 2 {
		return 0
	}
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].WindowEnd.Before(candidates[j].WindowEnd)
	})
	origin := candidates[0].WindowEnd
	meanX := 0.0
	meanY := 0.0
	for _, candidate := range candidates {
		meanX += candidate.WindowEnd.Sub(origin).Hours() / 24
		meanY += candidate.VibrationMMS
	}
	meanX /= float64(len(candidates))
	meanY /= float64(len(candidates))
	numerator := 0.0
	denominator := 0.0
	for _, candidate := range candidates {
		x := candidate.WindowEnd.Sub(origin).Hours()/24 - meanX
		y := candidate.VibrationMMS - meanY
		numerator += x * y
		denominator += x * x
	}
	if denominator == 0 {
		return 0
	}
	slopePerDay := numerator / denominator
	return math.Min(math.Max(0, slopePerDay/assetConfig.MaxVibrationMMS), 1.5)
}
