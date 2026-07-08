package report

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"example.com/fleetrisk/internal/domain"
)

type Manifest struct {
	GeneratedAt string            `json:"generated_at"`
	ModelID     string            `json:"model_id"`
	PolicyID    string            `json:"policy_id"`
	RowCount    int               `json:"row_count"`
	OutputFiles []string          `json:"output_files"`
	InputSHA256 map[string]string `json:"input_sha256"`
}

type Evaluation struct {
	RowCount            int                    `json:"row_count"`
	PositiveActionCount int                    `json:"positive_action_count"`
	ConfusionMatrix     ConfusionMatrix        `json:"confusion_matrix"`
	Metrics             Metrics                `json:"metrics"`
	SiteMetrics         map[string]SiteMetrics `json:"site_metrics"`
}

type ConfusionMatrix struct {
	TruePositive  int `json:"true_positive"`
	FalsePositive int `json:"false_positive"`
	TrueNegative  int `json:"true_negative"`
	FalseNegative int `json:"false_negative"`
}

type Metrics struct {
	Precision        float64 `json:"precision"`
	Recall           float64 `json:"recall"`
	F1               float64 `json:"f1"`
	BrierScore       float64 `json:"brier_score"`
	ROCAUC           float64 `json:"roc_auc"`
	AveragePrecision float64 `json:"average_precision"`
}

type SiteMetrics struct {
	Count                int     `json:"count"`
	PositiveActionCount  int     `json:"positive_action_count"`
	ObservedFailureCount int     `json:"observed_failure_count"`
	MeanCalibratedRisk   float64 `json:"mean_calibrated_risk"`
}

func WriteScored(path string, scored []domain.ScoredCall) error {
	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create %s: %w", path, err)
	}
	defer file.Close()
	writer := csv.NewWriter(file)
	defer writer.Flush()
	if err := writer.Write([]string{"request_id", "asset_id", "site", "opened_at", "priority", "raw_score", "calibrated_risk", "downtime_risk", "risk_band", "action", "top_factor"}); err != nil {
		return err
	}
	for _, item := range scored {
		row := []string{
			item.Call.RequestID,
			item.Call.AssetID,
			item.Call.Site,
			item.Call.OpenedAt.Format("2006-01-02T15:04:05Z"),
			item.Call.Priority,
			formatScore(item.RawScore),
			formatScore(item.CalibratedRisk),
			formatScore(item.DowntimeRisk),
			item.RiskBand,
			item.Action,
			item.TopFactor,
		}
		if err := writer.Write(row); err != nil {
			return err
		}
	}
	return writer.Error()
}

func WriteDecisions(path string, scored []domain.ScoredCall) error {
	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create %s: %w", path, err)
	}
	defer file.Close()
	writer := csv.NewWriter(file)
	defer writer.Flush()
	if err := writer.Write([]string{"request_id", "asset_id", "action", "risk_band", "calibrated_risk", "downtime_risk", "due_within_hours", "decision_value", "reason"}); err != nil {
		return err
	}
	for _, item := range scored {
		row := []string{
			item.Call.RequestID,
			item.Call.AssetID,
			item.Action,
			item.RiskBand,
			formatScore(item.CalibratedRisk),
			formatScore(item.DowntimeRisk),
			fmt.Sprintf("%d", item.DueWithinHours),
			formatScore(item.DecisionValue),
			item.TopFactor + ":" + item.RiskBand,
		}
		if err := writer.Write(row); err != nil {
			return err
		}
	}
	return writer.Error()
}

func WriteSchedule(path string, schedule []domain.ScheduledAction) error {
	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create %s: %w", path, err)
	}
	defer file.Close()
	writer := csv.NewWriter(file)
	defer writer.Flush()
	if err := writer.Write([]string{"request_id", "crew_id", "region", "site", "action", "start_at", "end_at", "travel_hours"}); err != nil {
		return err
	}
	for _, item := range schedule {
		row := []string{
			item.RequestID,
			item.CrewID,
			item.Region,
			item.Site,
			item.Action,
			item.StartAt.Format("2006-01-02T15:04:05Z"),
			item.EndAt.Format("2006-01-02T15:04:05Z"),
			formatScore(item.TravelHours),
		}
		if err := writer.Write(row); err != nil {
			return err
		}
	}
	return writer.Error()
}

func WriteParts(path string, allocations []domain.PartAllocation) error {
	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create %s: %w", path, err)
	}
	defer file.Close()
	writer := csv.NewWriter(file)
	defer writer.Flush()
	if err := writer.Write([]string{"request_id", "part_id", "source_site", "dest_site", "quantity", "ready_at", "transfer_hours"}); err != nil {
		return err
	}
	for _, item := range allocations {
		row := []string{
			item.RequestID,
			item.PartID,
			item.SourceSite,
			item.DestSite,
			fmt.Sprintf("%d", item.Quantity),
			item.ReadyAt.Format("2006-01-02T15:04:05Z"),
			formatScore(item.TransferHours),
		}
		if err := writer.Write(row); err != nil {
			return err
		}
	}
	return writer.Error()
}

func WriteJSON(path string, value any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create %s: %w", path, err)
	}
	defer file.Close()
	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(value)
}

func formatScore(value float64) string {
	return fmt.Sprintf("%.6f", value)
}
