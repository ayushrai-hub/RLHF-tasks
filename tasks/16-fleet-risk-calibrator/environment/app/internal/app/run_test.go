package app

import (
	"encoding/csv"
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"testing"
)

func TestRunMatchesFeatureMathSmokeFixture(t *testing.T) {
	dir := t.TempDir()
	writeFixture(t, dir, "model.json", `{
  "model_id": "smoke-model",
  "feature_params": {
    "trend_lookback_hours": 72,
    "temp_ewma_half_life_hours": 24,
    "history_lookback_days": 120,
    "history_half_life_days": 30
  },
  "heads": {
    "failure": {
      "intercept": -1.1,
      "weights": {
        "temp_over_limit": 0.8,
        "vibration_slope": 1.3,
        "repeat_repair_rate": 0.7,
        "history_decay": 0.9,
        "urgent_flag": 0.25,
        "heat_flag": 0.2,
        "pressure_drift": 0.5
      },
      "calibration": [
        {"raw": 0.0, "calibrated": 0.05},
        {"raw": 0.5, "calibrated": 0.55},
        {"raw": 1.0, "calibrated": 0.95}
      ]
    },
    "downtime": {
      "intercept": -0.8,
      "weights": {
        "vibration_ratio": 0.35,
        "runtime_log": 0.4,
        "current_z": 0.25,
        "tech_hours_scaled": 0.1
      },
      "calibration": [
        {"raw": 0.0, "calibrated": 0.02},
        {"raw": 0.5, "calibrated": 0.5},
        {"raw": 1.0, "calibrated": 0.9}
      ]
    }
  },
  "blend_by_asset_type": {
    "pump": {"failure": 0.7, "downtime": 0.3}
  },
  "asset_types": {
    "pump": {
      "temp_limit_c": 70,
      "max_vibration_mm_s": 10,
      "nominal_pressure_kpa": 100,
      "current_mean_a": 20,
      "current_std_a": 5,
      "impute_temp_c": 65
    }
  }
}`)
	writeFixture(t, dir, "policy.json", `{
  "policy_id": "smoke-policy",
  "report_generated_at": "2026-01-04T00:00:00Z",
  "thresholds": {
    "dispatch": 0.65,
    "inspect": 0.45,
    "watch": 0.25,
    "urgent_inspect_floor": 0.2
  },
  "due_hours": {
    "dispatch": 12,
    "inspect": 36,
    "monitor": 168
  },
  "optimizer": {
    "risk_effect": {"dispatch": 2.0, "inspect": 1.0, "monitor": 0.0},
    "downtime_effect": {"dispatch": 0.8, "inspect": 0.3, "monitor": 0.0},
    "action_cost": {"dispatch": 0.4, "inspect": 0.1, "monitor": 0.0},
    "minimum_risk": {"dispatch": 0.5, "inspect": 0.3},
    "site_region": {"LAB": "lab-region"},
    "regional_limits": {"lab-region": {"dispatch_slots": 1, "inspect_slots": 1, "crew_hours": 6.0}},
    "action_hours": {
      "dispatch": {"pump": 3.0},
      "inspect": {"pump": 1.0},
      "monitor": {"pump": 0.0}
    },
    "crew_roster": [
      {"crew_id": "LAB-1", "region": "lab-region", "home_site": "LAB", "shift_start": "2026-01-04T00:00:00Z", "shift_end": "2026-01-04T12:00:00Z", "max_continuous_hours": 4.0}
    ],
    "break_hours": 0.75,
    "travel_hours": {
      "lab-region": {"LAB": {"LAB": 0.0}}
    },
    "priority_bonus": {
      "urgent": {"dispatch": 0.2, "inspect": 0.1, "monitor": 0.0},
      "routine": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0}
    }
  }
}`)
	writeFixture(t, dir, "service_calls.csv", "request_id,asset_id,asset_type,site,opened_at,priority,technician_hours,notes_code\nSMOKE-1,A-1,pump,LAB,2026-01-03T06:00:00Z,urgent,6.0,HEAT\n")
	writeFixture(t, dir, "sensor_windows.csv", "asset_id,window_end,temp_c,vibration_mm_s,pressure_kpa,current_a,runtime_hours\nA-1,2026-01-01T00:00:00Z,66,2,98,18,90\nA-1,2026-01-02T00:00:00Z,78,5,104,22,120\nA-1,2026-01-03T00:00:00Z,,11,110,25,200\n")
	writeFixture(t, dir, "asset_history.csv", "asset_id,event_time,event_type,severity\nA-1,2025-12-20T06:00:00Z,corrective,2\nA-1,2025-12-25T06:00:00Z,failure,5\nA-1,2025-11-20T06:00:00Z,corrective,4\nA-1,2025-09-01T06:00:00Z,corrective,5\n")
	writeFixture(t, dir, "maintenance_labels.csv", "request_id,failure_within_30d\nSMOKE-1,1\n")
	writeFixture(t, dir, "site_capacity.csv", "site,dispatch_slots,inspect_slots\nLAB,1,1\n")

	outDir := filepath.Join(dir, "out")
	err := Run(Options{
		ModelPath:    filepath.Join(dir, "model.json"),
		PolicyPath:   filepath.Join(dir, "policy.json"),
		CallsPath:    filepath.Join(dir, "service_calls.csv"),
		WindowsPath:  filepath.Join(dir, "sensor_windows.csv"),
		HistoryPath:  filepath.Join(dir, "asset_history.csv"),
		LabelsPath:   filepath.Join(dir, "maintenance_labels.csv"),
		CapacityPath: filepath.Join(dir, "site_capacity.csv"),
		OutDir:       outDir,
	})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	scored := readRows(t, filepath.Join(outDir, "scored_calls.csv"))
	if len(scored) != 1 {
		t.Fatalf("got %d scored rows, want 1", len(scored))
	}
	row := scored[0]
	assertField(t, row, "raw_score", "0.709148")
	assertField(t, row, "calibrated_risk", "0.702318")
	assertField(t, row, "downtime_risk", "0.539299")
	assertField(t, row, "priority", "urgent")
	assertField(t, row, "risk_band", "high")
	assertField(t, row, "action", "dispatch")
	assertField(t, row, "top_factor", "vibration_slope")

	decisions := readRows(t, filepath.Join(outDir, "maintenance_decisions.csv"))
	if len(decisions) != 1 {
		t.Fatalf("got %d decision rows, want 1", len(decisions))
	}
	assertField(t, decisions[0], "due_within_hours", "12")
	assertField(t, decisions[0], "decision_value", "1.636076")

	var evaluation struct {
		ConfusionMatrix map[string]int     `json:"confusion_matrix"`
		Metrics         map[string]float64 `json:"metrics"`
	}
	bytes, err := os.ReadFile(filepath.Join(outDir, "evaluation.json"))
	if err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(bytes, &evaluation); err != nil {
		t.Fatal(err)
	}
	wantMatrix := map[string]int{"true_positive": 1, "false_positive": 0, "true_negative": 0, "false_negative": 0}
	for key, want := range wantMatrix {
		if evaluation.ConfusionMatrix[key] != want {
			t.Fatalf("confusion_matrix[%s] = %d, want %d", key, evaluation.ConfusionMatrix[key], want)
		}
	}
	if math.Abs(evaluation.Metrics["brier_score"]-0.08861436043491541) > 1e-12 {
		t.Fatalf("brier_score = %.17f", evaluation.Metrics["brier_score"])
	}
}

func writeFixture(t *testing.T, dir, name, contents string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(dir, name), []byte(contents), 0o644); err != nil {
		t.Fatal(err)
	}
}

func readRows(t *testing.T, path string) []map[string]string {
	t.Helper()
	file, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()
	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		t.Fatal(err)
	}
	if len(records) == 0 {
		t.Fatalf("%s had no rows", path)
	}
	header := records[0]
	rows := make([]map[string]string, 0, len(records)-1)
	for _, record := range records[1:] {
		row := make(map[string]string, len(header))
		for i, name := range header {
			row[name] = record[i]
		}
		rows = append(rows, row)
	}
	return rows
}

func assertField(t *testing.T, row map[string]string, key, want string) {
	t.Helper()
	if row[key] != want {
		t.Fatalf("%s = %q, want %q", key, row[key], want)
	}
}
