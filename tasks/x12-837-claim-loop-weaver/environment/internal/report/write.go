package report

import (
	"claim-weaver/internal/model"
)

func WriteOutputs(claimsPath, summaryPath string, woven model.WovenOutput, summary model.Summary) error {
	if err := WriteJSON(claimsPath, woven); err != nil {
		return err
	}
	return WriteJSON(summaryPath, summary)
}
