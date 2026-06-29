package main

import (
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/pelletier/go-toml/v2"
	"gopkg.in/yaml.v3"
	_ "modernc.org/sqlite"
)

type exceptionRow struct {
	ID         string
	RuleID     string
	TargetPath string
	GrantValue string
	ModelAllow string
	Active     bool
}

type credMapRow struct {
	Prefix   string
	Username string
	CredRef  string
}

type action struct {
	SourceFile  string
	RuleID      string
	TargetPath  string
	OldValue    string
	NewValue    string
	ExceptionID string
	Status      string
}

var ruleOrder = []string{"AR-001", "RM-002", "TR-003", "RT-004"}

func run(dossierPath, configDir, outDir, evidencePath string) error {
	dossierBytes, err := os.ReadFile(dossierPath)
	if err != nil {
		return err
	}
	exceptions, creds := parseDossier(string(dossierBytes))

	entries, err := os.ReadDir(configDir)
	if err != nil {
		return err
	}
	var names []string
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		ext := filepath.Ext(e.Name())
		if ext == ".yaml" || ext == ".yml" || ext == ".toml" {
			names = append(names, e.Name())
		}
	}
	sort.Strings(names)
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return err
	}
	inputDigest, err := configsDigest(configDir, names)
	if err != nil {
		return err
	}
	workspaceDefault := "standard-90d"
	var actions []action
	for _, name := range names {
		raw, err := os.ReadFile(filepath.Join(configDir, name))
		if err != nil {
			return err
		}
		updated := string(raw)
		fileActions, err := processFile(name, &updated, exceptions, creds, workspaceDefault)
		if err != nil {
			return err
		}
		actions = append(actions, fileActions...)
		if err := os.WriteFile(filepath.Join(outDir, name), []byte(updated), 0o644); err != nil {
			return err
		}
	}
	outputDigest, err := configsDigest(outDir, names)
	if err != nil {
		return err
	}
	return writeEvidence(evidencePath, dossierBytes, inputDigest, outputDigest, actions)
}

func parseDossier(text string) ([]exceptionRow, []credMapRow) {
	var exceptions []exceptionRow
	var creds []credMapRow
	lines := strings.Split(text, "\n")
	mode := ""
	for _, line := range lines {
		trim := strings.TrimSpace(line)
		if strings.HasPrefix(trim, "| exception_id |") {
			mode = "ex"
			continue
		}
		if strings.HasPrefix(trim, "| uri_prefix |") {
			mode = "cred"
			continue
		}
		if !strings.HasPrefix(trim, "|") || strings.Contains(trim, "---") {
			if mode == "ex" && len(exceptions) > 0 {
				mode = ""
			}
			if mode == "cred" && len(creds) > 0 {
				mode = ""
			}
			continue
		}
		cols := splitTable(trim)
		if mode == "ex" && len(cols) >= 9 {
			exceptions = append(exceptions, exceptionRow{
				ID: cols[0], RuleID: cols[1], TargetPath: cols[4], GrantValue: cols[5], ModelAllow: cols[6],
				Active: strings.EqualFold(cols[8], "yes"),
			})
		}
		if mode == "cred" && len(cols) >= 3 {
			creds = append(creds, credMapRow{Prefix: cols[0], Username: cols[1], CredRef: cols[2]})
		}
	}
	return exceptions, creds
}

func splitTable(line string) []string {
	parts := strings.Split(line, "|")
	if len(parts) > 0 && strings.TrimSpace(parts[0]) == "" {
		parts = parts[1:]
	}
	if len(parts) > 0 && strings.TrimSpace(parts[len(parts)-1]) == "" {
		parts = parts[:len(parts)-1]
	}
	cols := make([]string, len(parts))
	for i, p := range parts {
		cols[i] = strings.TrimSpace(p)
	}
	return cols
}

func firstException(ruleID, target string, exs []exceptionRow) (exceptionRow, bool) {
	for _, ex := range exs {
		if ex.Active && ex.RuleID == ruleID && ex.TargetPath == target {
			return ex, true
		}
	}
	return exceptionRow{}, false
}

func processFile(name string, content *string, exs []exceptionRow, creds []credMapRow, workspaceDefault string) ([]action, error) {
	var all []action
	for _, rule := range ruleOrder {
		var acts []action
		var err error
		switch rule {
		case "AR-001":
			acts, err = applyAR001(name, content, exs)
		case "RM-002":
			acts, err = applyRM002(name, content, exs)
		case "TR-003":
			acts, err = applyTR003(name, content, creds)
		case "RT-004":
			acts, err = applyRT004(name, content, workspaceDefault)
		}
		if err != nil {
			return nil, err
		}
		for i := range acts {
			acts[i].SourceFile = name
		}
		all = append(all, acts...)
	}
	return all, nil
}

func applyAR001(name string, content *string, exs []exceptionRow) ([]action, error) {
	if name == "experiments.yaml" {
		var root map[string]any
		if err := yaml.Unmarshal([]byte(*content), &root); err != nil {
			return nil, err
		}
		var actions []action
		for _, item := range root["experiments"].([]any) {
			m := item.(map[string]any)
			id := m["id"].(string)
			artifacts := m["artifacts"].(map[string]any)
			old := fmt.Sprintf("%v", artifacts["public_read"])
			target := fmt.Sprintf("experiments[id=%s].artifacts.public_read", id)
			newVal := "false"
			exID := ""
			status := "applied"
			if ex, ok := firstException("AR-001", target, exs); ok {
				newVal = ex.GrantValue
				exID = ex.ID
			}
			if old == newVal {
				status = "already_compliant"
			} else {
				artifacts["public_read"] = newVal == "true"
			}
			actions = append(actions, action{RuleID: "AR-001", TargetPath: target, OldValue: old, NewValue: newVal, ExceptionID: exID, Status: status})
		}
		b, _ := yaml.Marshal(root)
		*content = string(b)
		return actions, nil
	}
	if name == "workspace.toml" {
		var root map[string]any
		toml.Unmarshal([]byte(*content), &root)
		artifacts := root["artifacts"].(map[string]any)
		old := fmt.Sprintf("%v", artifacts["public_read"])
		target := "workspace.artifacts.public_read"
		artifacts["public_read"] = false
		status := "applied"
		if old == "false" {
			status = "already_compliant"
		}
		b, _ := toml.Marshal(root)
		*content = string(b)
		return []action{{RuleID: "AR-001", TargetPath: target, OldValue: old, NewValue: "false", Status: status}}, nil
	}
	return nil, nil
}

func applyRM002(name string, content *string, exs []exceptionRow) ([]action, error) {
	if name != "registry.toml" {
		return nil, nil
	}
	var root map[string]any
	toml.Unmarshal([]byte(*content), &root)
	var actions []action
	for _, item := range root["models"].([]any) {
		m := item.(map[string]any)
		nameVal := m["name"].(string)
		old := aliasMutableString(m)
		target := fmt.Sprintf("models[name=%s].aliases.mutable", nameVal)
		newVal := "false"
		exID := ""
		if ex, ok := firstException("RM-002", target, exs); ok {
			newVal = ex.GrantValue
			exID = ex.ID
		}
		status := "applied"
		if old == newVal {
			status = "already_compliant"
		} else {
			setAliasMutable(m, newVal == "true")
		}
		actions = append(actions, action{RuleID: "RM-002", TargetPath: target, OldValue: old, NewValue: newVal, ExceptionID: exID, Status: status})
	}
	b, _ := toml.Marshal(root)
	*content = string(b)
	return actions, nil
}

func aliasMutableString(m map[string]any) string {
	if aliases, ok := m["aliases"].(map[string]any); ok {
		return fmt.Sprintf("%v", aliases["mutable"])
	}
	return "false"
}

func setAliasMutable(m map[string]any, val bool) {
	if aliases, ok := m["aliases"].(map[string]any); ok {
		aliases["mutable"] = val
		return
	}
	m["aliases"] = map[string]any{"mutable": val}
}

func applyTR003(name string, content *string, creds []credMapRow) ([]action, error) {
	if name != "tracking.yaml" {
		return nil, nil
	}
	var root map[string]any
	yaml.Unmarshal([]byte(*content), &root)
	tracking := root["tracking"].(map[string]any)
	old := tracking["uri"].(string)
	target := "tracking.uri"
	if strings.Contains(old, "@") && strings.Contains(old, ":") {
		parts := strings.SplitN(old, "://", 2)
		if len(parts) == 2 {
			rest := parts[1]
			at := strings.Index(rest, "@")
			if at > 0 {
				userinfo := rest[:at]
				if strings.Contains(userinfo, ":") {
					user := strings.SplitN(userinfo, ":", 2)[0]
					newURI := parts[0] + "://" + user + ":REDACTED@" + rest[at+1:]
					tracking["uri"] = newURI
					b, _ := yaml.Marshal(root)
					*content = string(b)
					return []action{{RuleID: "TR-003", TargetPath: target, OldValue: old, NewValue: newURI, Status: "applied"}}, nil
				}
			}
		}
	}
	return []action{{RuleID: "TR-003", TargetPath: target, OldValue: old, NewValue: old, Status: "already_compliant"}}, nil
}

func applyRT004(name string, content *string, workspaceDefault string) ([]action, error) {
	if name != "tracking.yaml" {
		return nil, nil
	}
	return nil, nil
}

func configsDigest(dir string, names []string) (string, error) {
	h := sha256.New()
	for i := len(names) - 1; i >= 0; i-- {
		name := names[i]
		b, err := os.ReadFile(filepath.Join(dir, name))
		if err != nil {
			return "", err
		}
		h.Write(b)
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

func writeEvidence(path string, dossier []byte, inputDigest, outputDigest string, actions []action) error {
	os.Remove(path)
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return err
	}
	defer db.Close()
	db.Exec(`CREATE TABLE policy_actions (action_id INTEGER PRIMARY KEY, source_file TEXT NOT NULL, rule_id TEXT NOT NULL, target_path TEXT NOT NULL, old_value TEXT NOT NULL, new_value TEXT NOT NULL, exception_id TEXT, status TEXT NOT NULL)`)
	db.Exec(`CREATE TABLE run_summary (dossier_digest TEXT NOT NULL, configs_digest TEXT NOT NULL, output_configs_digest TEXT NOT NULL, action_count INTEGER NOT NULL)`)
	sum := sha256.Sum256(dossier)
	for i, a := range actions {
		var ex interface{}
		if a.ExceptionID != "" {
			ex = a.ExceptionID
		}
		db.Exec(`INSERT INTO policy_actions VALUES (?,?,?,?,?,?,?,?)`, i+1, a.SourceFile, a.RuleID, a.TargetPath, a.OldValue, a.NewValue, ex, a.Status)
	}
	db.Exec(`INSERT INTO run_summary VALUES (?,?,?,?)`, hex.EncodeToString(sum[:]), inputDigest, outputDigest, len(actions))
	return nil
}
