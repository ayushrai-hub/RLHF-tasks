package output

import (
	"encoding/json"
	"fmt"
	"os"

	"transitivity-checker/pkg/types"
)

// WriteJSON serializes the analysis result to a JSON file.
func WriteJSON(result types.AnalysisResult, path string) error {
	data, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal error: %w", err)
	}
	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("write error: %w", err)
	}
	return nil
}

// FormatSummary returns a human-readable summary string.
func FormatSummary(result types.AnalysisResult) string {
	return fmt.Sprintf("Rules: %d | Obligations: %d | Unprovable: %d | Transitivity: %v",
		result.TotalRules, len(result.Obligations),
		result.UnprovableCount, result.TransitivityHolds)
}
