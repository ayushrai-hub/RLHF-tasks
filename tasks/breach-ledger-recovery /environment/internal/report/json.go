package report

import (
	"encoding/json"
	"os"
	"path/filepath"

	"breach-ledger/internal/model"
)

func R1(out string, ev model.Evidence) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	payload := map[string]any{
		"schema_version":       2,
		"status":               "accepted",
		"classification":       "unclassified",
		"initial_access":       ev.InitialAccess,
		"compromised_hosts":    ev.CompromisedHosts,
		"compromised_accounts": ev.CompromisedUsers,
		"commands":             ev.Commands,
		"persistence":          ev.Persistence,
		"stolen_files":         ev.StolenFiles,
		"stolen_secrets":       ev.StolenSecrets,
		"exfiltration":         ev.Exfiltration,
		"iocs":                 ev.IOCs,
		"false_leads":          ev.FalseLeads,
		"tampered_events":      ev.TamperedEvents,
		"modified_configs":     ev.ModifiedConfigs,
		"parse_summary":        ev.Summary,
	}
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(out, "incident_report.json"), append(data, '\n'), 0o644)
}

func R0(out string, issue model.Issue) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	data, _ := json.MarshalIndent(map[string]any{
		"schema_version": 2,
		"status":         "rejected",
		"error": map[string]any{
			"code":    issue.Code,
			"message": issue.Message,
		},
	}, "", "  ")
	return os.WriteFile(filepath.Join(out, "incident_report.json"), append(data, '\n'), 0o644)
}
