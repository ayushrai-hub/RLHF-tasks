package report

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"breach-ledger/internal/model"
)

func R4(out string, ev model.Evidence) error {
	actions := []string{
		"disable_account:backup",
		"patch:CVE-2025-4178",
		"rotate_secret:token",
	}
	for _, item := range ev.Persistence {
		actions = append(actions, "remove:"+item)
	}
	for _, config := range ev.ModifiedConfigs {
		actions = append(actions, "restore_config:"+config)
	}
	for _, ioc := range ev.IOCs {
		if strings.HasPrefix(ioc, "ip:") {
			actions = append(actions, "block_"+ioc)
		}
	}
	for _, file := range ev.StolenFiles {
		actions = append(actions, "review_file:"+file)
	}
	sort.Strings(actions)
	payload := map[string]any{
		"schema_version":         2,
		"golden_config_changed":  ev.CfgFlag,
		"actions":                actions,
		"modified_config_count":  len(ev.ModifiedConfigs),
		"persistence_item_count": len(ev.Persistence),
	}
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(out, "remediation_plan.json"), append(data, '\n'), 0o644)
}
