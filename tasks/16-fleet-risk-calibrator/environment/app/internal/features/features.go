package features

import (
	"fmt"
	"math"

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
	temp := assetConfig.ImputeTempC
	if window.TempC != nil {
		temp = *window.TempC
	}

	values := map[string]float64{
		"temp_over_limit":    math.Max(0, temp-assetConfig.TempLimitC) / 10,
		"vibration_ratio":    window.VibrationMMS / assetConfig.MaxVibrationMMS,
		"pressure_delta":     math.Abs(window.PressureKPA-assetConfig.NominalPressureKPA) / assetConfig.NominalPressureKPA,
		"current_z":          0,
		"runtime_log":        0,
		"urgent_flag":        0,
		"rework_flag":        0,
		"tech_hours_scaled":  call.TechnicianHours / 4,
		"temp_rise":          0,
		"repeat_repair_rate": 0,
		"severity_memory":    0,
		"vibration_slope":    0,
		"history_decay":      0,
		"leak_flag":          0,
		"heat_flag":          0,
		"pressure_drift":     0,
	}
	_ = allWindows
	_ = history
	return values, nil
}
