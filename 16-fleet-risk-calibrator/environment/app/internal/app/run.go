package app

import (
	"os"
	"path/filepath"

	"example.com/fleetrisk/internal/config"
	"example.com/fleetrisk/internal/csvutil"
	"example.com/fleetrisk/internal/domain"
	"example.com/fleetrisk/internal/report"
)

type Options struct {
	ModelPath    string
	PolicyPath   string
	CallsPath    string
	WindowsPath  string
	HistoryPath  string
	LabelsPath   string
	CapacityPath string
	OutDir       string
}

func Run(opts Options) error {
	modelConfig, err := config.LoadModel(opts.ModelPath)
	if err != nil {
		return err
	}
	policy, err := config.LoadPolicy(opts.PolicyPath)
	if err != nil {
		return err
	}
	calls, err := csvutil.LoadServiceCalls(opts.CallsPath)
	if err != nil {
		return err
	}
	windows, err := csvutil.LoadSensorWindows(opts.WindowsPath)
	if err != nil {
		return err
	}
	history, err := csvutil.LoadHistory(opts.HistoryPath)
	if err != nil {
		return err
	}
	labels, err := csvutil.LoadLabels(opts.LabelsPath)
	if err != nil {
		return err
	}
	capacity, err := csvutil.LoadCapacity(opts.CapacityPath)
	if err != nil {
		return err
	}
	_ = windows
	_ = history
	_ = labels
	_ = capacity

	scored := make([]domain.ScoredCall, 0, len(calls))
	for _, call := range calls {
		scored = append(scored, domain.ScoredCall{
			Call:           call,
			RawScore:       0,
			CalibratedRisk: 0,
			DowntimeRisk:   0,
			RiskBand:       "low",
			Action:         "monitor",
			TopFactor:      "none",
			DueWithinHours: policy.DueHours.Monitor,
			DecisionValue:  0,
		})
	}

	if err := os.MkdirAll(opts.OutDir, 0o755); err != nil {
		return err
	}
	if err := report.WriteScored(filepath.Join(opts.OutDir, "scored_calls.csv"), scored); err != nil {
		return err
	}
	if err := report.WriteDecisions(filepath.Join(opts.OutDir, "maintenance_decisions.csv"), scored); err != nil {
		return err
	}
	if err := report.WriteParts(filepath.Join(opts.OutDir, "parts_allocation.csv"), nil); err != nil {
		return err
	}
	if err := report.WriteJSON(filepath.Join(opts.OutDir, "risk_manifest.json"), report.Manifest{
		GeneratedAt: policy.ReportGeneratedAt,
		ModelID:     modelConfig.ModelID,
		PolicyID:    policy.PolicyID,
		RowCount:    len(scored),
		OutputFiles: []string{"scored_calls.csv", "maintenance_decisions.csv", "crew_schedule.csv", "parts_allocation.csv", "risk_manifest.json", "evaluation.json"},
		InputSHA256: map[string]string{},
	}); err != nil {
		return err
	}
	return report.WriteJSON(filepath.Join(opts.OutDir, "evaluation.json"), report.Evaluation{
		RowCount:    len(scored),
		SiteMetrics: map[string]report.SiteMetrics{},
	})
}
