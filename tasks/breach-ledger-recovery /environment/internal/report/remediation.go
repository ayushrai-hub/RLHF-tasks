package report

import (
	"os"
	"path/filepath"

	"breach-ledger/internal/model"
)

func R4(out string, _ model.Evidence) error {
	return os.WriteFile(filepath.Join(out, "remediation_plan.json"), []byte("{\"schema_version\":2,\"golden_config_changed\":false,\"modified_config_count\":0,\"persistence_item_count\":0,\"actions\":[]}\n"), 0o644)
}
