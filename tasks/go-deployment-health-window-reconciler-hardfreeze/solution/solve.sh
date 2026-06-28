#!/usr/bin/env bash
set -euo pipefail
cd /app
cat > /app/cmd/reconciler/main.go <<'GO'
package main

import (
	"bufio"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

const generatedBy = "go-deployment-health-window-reconciler"

type Config struct {
	DefaultDurationMinutes  int               `json:"default_duration_minutes"`
	RollbackGraceMinutes    int               `json:"rollback_grace_minutes"`
	RequiredProbeTypes      []string          `json:"required_probe_types"`
	EnvironmentAliases      map[string]string `json:"environment_aliases"`
	ProbeTypeAliases        map[string]string `json:"probe_type_aliases"`
	ProbeStatusAliases      map[string]string `json:"probe_status_aliases"`
	RollbackStateAliases    map[string]string `json:"rollback_state_aliases"`
	IncidentSeverityAliases map[string]string `json:"incident_severity_aliases"`
}

type Source struct {
	Path string
	Line int
}

type Deployment struct {
	ID            string
	Service       string
	Environment   string
	ReleaseID     string
	Owner         string
	StartedAt     time.Time
	DurationMins  int
	RequiredTypes []string
	DependsOn     []string
	Priority      int
	Source        Source
}

type Probe struct {
	ID           string
	DeploymentID string
	Service      string
	Environment  string
	Type         string
	CheckedAt    time.Time
	Status       string
	Source       Source
}

type Incident struct {
	ID           string
	DeploymentID string
	StartedAt    time.Time
	EndedAt      *time.Time
	Severity     string
	Source       Source
}

type Rollback struct {
	ID           string
	DeploymentID string
	MarkedAt     time.Time
	State        string
	Source       Source
}

type Freeze struct {
	ID            string
	Environment   string
	Service       string
	StartsAt      time.Time
	EndsAt        time.Time
	Severity      string
	AllowedOwners []string
	Source        Source
}

type Warning struct {
	Code       string `json:"code"`
	Severity   string `json:"severity"`
	SubjectID  string `json:"subject_id"`
	SourcePath string `json:"source_path"`
	SourceLine int    `json:"source_line"`
	Detail     string `json:"detail"`
}

type Window struct {
	DeploymentID        string   `json:"deployment_id"`
	Service             string   `json:"service"`
	Environment         string   `json:"environment"`
	ReleaseID           string   `json:"release_id"`
	Owner               string   `json:"owner"`
	WindowStart         string   `json:"window_start"`
	WindowEnd           string   `json:"window_end"`
	DurationMinutes     int      `json:"duration_minutes"`
	RequiredProbeTypes  []string `json:"required_probe_types"`
	ObservedProbeIDs    []string `json:"observed_probe_ids"`
	MissingProbeTypes   []string `json:"missing_probe_types"`
	FailedProbeIDs      []string `json:"failed_probe_ids"`
	IncidentIDs              []string `json:"incident_ids"`
	DependsOn                []string `json:"depends_on"`
	FreezeWindowIDs          []string `json:"freeze_window_ids"`
	PolicyViolationCodes     []string `json:"policy_violation_codes"`
	BaseHealthState          string   `json:"base_health_state"`
	BlockedByDeploymentIDs   []string `json:"blocked_by_deployment_ids"`
	RollbackMarkerID         *string  `json:"rollback_marker_id"`
	RollbackEffectiveAt      *string  `json:"rollback_effective_at"`
	HealthState              string   `json:"health_state"`
}

type HealthSummary struct {
	DeploymentsTotal int `json:"deployments_total"`
	WindowsTotal     int `json:"windows_total"`
	HealthyCount    int `json:"healthy_count"`
	DegradedCount   int `json:"degraded_count"`
	FailedCount     int `json:"failed_count"`
	RolledBackCount      int `json:"rolled_back_count"`
	BlockedCount         int `json:"blocked_count"`
	FrozenCount          int `json:"frozen_count"`
	PolicyViolationCount int `json:"policy_violation_count"`
	WarningsTotal        int `json:"warnings_total"`
}

type HealthReport struct {
	GeneratedBy string        `json:"generated_by"`
	Summary     HealthSummary `json:"summary"`
	Windows     []Window      `json:"windows"`
}

type WarningReport struct {
	GeneratedBy string    `json:"generated_by"`
	Warnings    []Warning `json:"warnings"`
}

func main() {
	configPath := flag.String("config", "", "config path")
	inputPath := flag.String("input", "", "input directory")
	outPath := flag.String("out", "", "output directory")
	flag.Parse()

	if *configPath == "" || *inputPath == "" || *outPath == "" {
		fmt.Fprintln(os.Stderr, "--config, --input, and --out are required")
		os.Exit(2)
	}

	cfg, err := loadConfig(*configPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	health, warnings, err := reconcile(cfg, *inputPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	health.Summary.WarningsTotal = len(warnings.Warnings)

	if err := prepareOutput(*outPath); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := writeJSON(filepath.Join(*outPath, "health_windows.json"), health); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := writeJSON(filepath.Join(*outPath, "reconciliation_warnings.json"), warnings); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func loadConfig(path string) (Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Config{}, err
	}
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return Config{}, err
	}
	if cfg.DefaultDurationMinutes <= 0 {
		cfg.DefaultDurationMinutes = 30
	}
	if cfg.RollbackGraceMinutes < 0 {
		cfg.RollbackGraceMinutes = 0
	}
	cfg.RequiredProbeTypes = canonicalStringSet(cfg.RequiredProbeTypes, cfg.ProbeTypeAliases)
	return cfg, nil
}

func reconcile(cfg Config, input string) (HealthReport, WarningReport, error) {
	deployments := map[string]Deployment{}
	probes := []Probe{}
	incidents := []Incident{}
	rollbacks := []Rollback{}
	freezes := []Freeze{}
	warnings := []Warning{}

	err := filepath.WalkDir(input, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if d.IsDir() || !strings.HasSuffix(strings.ToLower(d.Name()), ".jsonl") {
			return nil
		}
		kind := classify(d.Name())
		if kind == "" {
			return nil
		}
		rel, err := filepath.Rel(input, path)
		if err != nil {
			return err
		}
		rel = filepath.ToSlash(rel)
		return readJSONL(path, rel, kind, func(raw map[string]any, src Source) {
			switch kind {
			case "deployment":
				dep, warn, ok := parseDeployment(raw, src, cfg)
				if warn != nil {
					warnings = append(warnings, *warn)
				}
				if ok {
					if kept, exists := deployments[dep.ID]; exists {
						if deploymentWins(dep, kept) {
							warnings = append(warnings, duplicateWarning(kept, dep))
							deployments[dep.ID] = dep
						} else {
							warnings = append(warnings, duplicateWarning(dep, kept))
						}
					} else {
						deployments[dep.ID] = dep
					}
				}
			case "probe":
				probe, warn, ok := parseProbe(raw, src, cfg)
				if warn != nil {
					warnings = append(warnings, *warn)
				}
				if ok {
					probes = append(probes, probe)
				}
			case "incident":
				incident, warn, ok := parseIncident(raw, src, cfg)
				if warn != nil {
					warnings = append(warnings, *warn)
				}
				if ok {
					incidents = append(incidents, incident)
				}
			case "rollback":
				rollback, warn, ok := parseRollback(raw, src, cfg)
				if warn != nil {
					warnings = append(warnings, *warn)
				}
				if ok {
					rollbacks = append(rollbacks, rollback)
				}
			case "freeze":
				freeze, warn, ok := parseFreeze(raw, src, cfg)
				if warn != nil {
					warnings = append(warnings, *warn)
				}
				if ok {
					freezes = append(freezes, freeze)
				}
			}
		}, func(src Source) {
			warnings = append(warnings, Warning{
				Code: "malformed_json", Severity: "error", SubjectID: "",
				SourcePath: src.Path, SourceLine: src.Line,
				Detail: fmt.Sprintf("malformed JSON in %s row", kind),
			})
		})
	})
	if err != nil {
		return HealthReport{}, WarningReport{}, err
	}

	usableProbes, usableIncidents, usableRollbacks, eventWarnings := filterEvents(deployments, probes, incidents, rollbacks)
	warnings = append(warnings, eventWarnings...)

	windows := []Window{}
	for _, dep := range deployments {
		window, extraWarnings := buildWindow(dep, usableProbes, usableIncidents, usableRollbacks, cfg)
		warnings = append(warnings, extraWarnings...)
		windows = append(windows, window)
	}
	warnings = append(warnings, applyDependencyOverlay(windows, deployments)...)
	applyFreezeOverlay(windows, deployments, freezes)

	sort.Slice(windows, func(i, j int) bool {
		a := windows[i]
		b := windows[j]
		keysA := []string{a.Environment, a.Service, a.WindowStart, a.DeploymentID}
		keysB := []string{b.Environment, b.Service, b.WindowStart, b.DeploymentID}
		for idx := range keysA {
			if keysA[idx] != keysB[idx] {
				return keysA[idx] < keysB[idx]
			}
		}
		return false
	})
	sortWarnings(warnings)

	summary := HealthSummary{DeploymentsTotal: len(deployments), WindowsTotal: len(windows)}
	for _, window := range windows {
		switch window.HealthState {
		case "healthy":
			summary.HealthyCount++
		case "degraded":
			summary.DegradedCount++
		case "failed":
			summary.FailedCount++
		case "rolled_back":
			summary.RolledBackCount++
		case "blocked":
			summary.BlockedCount++
		case "frozen":
			summary.FrozenCount++
		}
		summary.PolicyViolationCount += len(window.PolicyViolationCodes)
	}
	report := HealthReport{GeneratedBy: generatedBy, Summary: summary, Windows: windows}
	warningReport := WarningReport{GeneratedBy: generatedBy, Warnings: warnings}
	return report, warningReport, nil
}

func classify(name string) string {
	lower := strings.ToLower(name)
	switch {
	case strings.Contains(lower, "deployment"):
		return "deployment"
	case strings.Contains(lower, "probe"):
		return "probe"
	case strings.Contains(lower, "incident"):
		return "incident"
	case strings.Contains(lower, "rollback"):
		return "rollback"
	case strings.Contains(lower, "freeze"):
		return "freeze"
	default:
		return ""
	}
}

func readJSONL(path, rel, kind string, row func(map[string]any, Source), malformed func(Source)) error {
	file, err := os.Open(path)
	if err != nil {
		return err
	}
	defer file.Close()
	scanner := bufio.NewScanner(file)
	line := 0
	for scanner.Scan() {
		line++
		text := strings.TrimSpace(scanner.Text())
		if text == "" {
			continue
		}
		src := Source{Path: rel, Line: line}
		var raw map[string]any
		if err := json.Unmarshal([]byte(text), &raw); err != nil {
			malformed(src)
			continue
		}
		row(raw, src)
	}
	return scanner.Err()
}

func parseDeployment(raw map[string]any, src Source, cfg Config) (Deployment, *Warning, bool) {
	id := optionalString(raw, "deployment_id")
	service := optionalString(raw, "service")
	environment := optionalString(raw, "environment")
	startedRaw := optionalString(raw, "started_at")
	for _, field := range []struct{ name, value string }{{"deployment_id", id}, {"service", service}, {"environment", environment}, {"started_at", startedRaw}} {
		if field.value == "" {
			return Deployment{}, invalidWarning("deployment", id, src, "missing required field "+field.name), false
		}
	}
	startedAt, err := parseTimestamp(startedRaw)
	if err != nil {
		return Deployment{}, invalidWarning("deployment", id, src, "invalid timestamp started_at"), false
	}
	duration := cfg.DefaultDurationMinutes
	if _, ok := raw["duration_minutes"]; ok && raw["duration_minutes"] != nil {
		parsed, err := intValue(raw["duration_minutes"])
		if err != nil || parsed <= 0 {
			return Deployment{}, invalidWarning("deployment", id, src, "duration_minutes must be positive"), false
		}
		duration = parsed
	}
	priority := 0
	if _, ok := raw["priority"]; ok && raw["priority"] != nil {
		parsed, err := intValue(raw["priority"])
		if err == nil {
			priority = parsed
		}
	}
	required := stringArray(raw["required_probes"])
	if len(required) == 0 {
		required = append([]string{}, cfg.RequiredProbeTypes...)
	} else {
		required = canonicalStringSet(required, cfg.ProbeTypeAliases)
	}
	dependsOn := plainStringSet(stringArray(raw["depends_on"]))
	return Deployment{
		ID: id, Service: service, Environment: canonical(environment, cfg.EnvironmentAliases),
		ReleaseID: optionalString(raw, "release_id"), Owner: optionalString(raw, "owner"),
		StartedAt: startedAt, DurationMins: duration, RequiredTypes: required, DependsOn: dependsOn,
		Priority: priority, Source: src,
	}, nil, true
}

func parseProbe(raw map[string]any, src Source, cfg Config) (Probe, *Warning, bool) {
	id := optionalString(raw, "probe_id")
	deploymentID := optionalString(raw, "deployment_id")
	probeType := optionalString(raw, "probe_type")
	checkedRaw := optionalString(raw, "checked_at")
	statusRaw := optionalString(raw, "status")
	for _, field := range []struct{ name, value string }{{"probe_id", id}, {"deployment_id", deploymentID}, {"probe_type", probeType}, {"checked_at", checkedRaw}, {"status", statusRaw}} {
		if field.value == "" {
			return Probe{}, invalidWarning("probe", id, src, "missing required field "+field.name), false
		}
	}
	checkedAt, err := parseTimestamp(checkedRaw)
	if err != nil {
		return Probe{}, invalidWarning("probe", id, src, "invalid timestamp checked_at"), false
	}
	status := canonical(statusRaw, cfg.ProbeStatusAliases)
	if status != "pass" && status != "fail" {
		return Probe{}, invalidWarning("probe", id, src, "status must canonicalize to pass or fail"), false
	}
	env := optionalString(raw, "environment")
	if env != "" {
		env = canonical(env, cfg.EnvironmentAliases)
	}
	return Probe{ID: id, DeploymentID: deploymentID, Service: optionalString(raw, "service"), Environment: env, Type: canonical(probeType, cfg.ProbeTypeAliases), CheckedAt: checkedAt, Status: status, Source: src}, nil, true
}

func parseIncident(raw map[string]any, src Source, cfg Config) (Incident, *Warning, bool) {
	id := optionalString(raw, "incident_id")
	deploymentID := optionalString(raw, "deployment_id")
	startedRaw := optionalString(raw, "started_at")
	severityRaw := optionalString(raw, "severity")
	for _, field := range []struct{ name, value string }{{"incident_id", id}, {"deployment_id", deploymentID}, {"started_at", startedRaw}, {"severity", severityRaw}} {
		if field.value == "" {
			return Incident{}, invalidWarning("incident", id, src, "missing required field "+field.name), false
		}
	}
	startedAt, err := parseTimestamp(startedRaw)
	if err != nil {
		return Incident{}, invalidWarning("incident", id, src, "invalid timestamp started_at"), false
	}
	var ended *time.Time
	endedRaw := optionalString(raw, "ended_at")
	if endedRaw != "" {
		parsed, err := parseTimestamp(endedRaw)
		if err != nil {
			return Incident{}, invalidWarning("incident", id, src, "invalid timestamp ended_at"), false
		}
		if parsed.Before(startedAt) {
			return Incident{}, invalidWarning("incident", id, src, "ended_at before started_at"), false
		}
		ended = &parsed
	}
	severity := canonical(severityRaw, cfg.IncidentSeverityAliases)
	if severity == "" {
		return Incident{}, invalidWarning("incident", id, src, "missing required field severity"), false
	}
	return Incident{ID: id, DeploymentID: deploymentID, StartedAt: startedAt, EndedAt: ended, Severity: severity, Source: src}, nil, true
}

func parseRollback(raw map[string]any, src Source, cfg Config) (Rollback, *Warning, bool) {
	id := optionalString(raw, "rollback_id")
	deploymentID := optionalString(raw, "deployment_id")
	markedRaw := optionalString(raw, "marked_at")
	stateRaw := optionalString(raw, "state")
	for _, field := range []struct{ name, value string }{{"rollback_id", id}, {"deployment_id", deploymentID}, {"marked_at", markedRaw}, {"state", stateRaw}} {
		if field.value == "" {
			return Rollback{}, invalidWarning("rollback", id, src, "missing required field "+field.name), false
		}
	}
	markedAt, err := parseTimestamp(markedRaw)
	if err != nil {
		return Rollback{}, invalidWarning("rollback", id, src, "invalid timestamp marked_at"), false
	}
	state := canonical(stateRaw, cfg.RollbackStateAliases)
	if state != "applied" && state != "pending" && state != "canceled" {
		return Rollback{}, invalidWarning("rollback", id, src, "state is not recognized"), false
	}
	return Rollback{ID: id, DeploymentID: deploymentID, MarkedAt: markedAt, State: state, Source: src}, nil, true
}

func parseFreeze(raw map[string]any, src Source, cfg Config) (Freeze, *Warning, bool) {
	id := optionalString(raw, "freeze_id")
	environment := optionalString(raw, "environment")
	startsRaw := optionalString(raw, "starts_at")
	endsRaw := optionalString(raw, "ends_at")
	severityRaw := optionalString(raw, "severity")
	for _, field := range []struct{ name, value string }{{"freeze_id", id}, {"environment", environment}, {"starts_at", startsRaw}, {"ends_at", endsRaw}, {"severity", severityRaw}} {
		if field.value == "" {
			return Freeze{}, invalidWarning("freeze", id, src, "missing required field "+field.name), false
		}
	}
	startsAt, err := parseTimestamp(startsRaw)
	if err != nil {
		return Freeze{}, invalidWarning("freeze", id, src, "invalid timestamp starts_at"), false
	}
	endsAt, err := parseTimestamp(endsRaw)
	if err != nil {
		return Freeze{}, invalidWarning("freeze", id, src, "invalid timestamp ends_at"), false
	}
	if endsAt.Before(startsAt) {
		return Freeze{}, invalidWarning("freeze", id, src, "ends_at before starts_at"), false
	}
	severity := strings.ToLower(strings.TrimSpace(severityRaw))
	if severity != "advisory" && severity != "hard" {
		return Freeze{}, invalidWarning("freeze", id, src, "severity must be advisory or hard"), false
	}
	return Freeze{ID: id, Environment: canonical(environment, cfg.EnvironmentAliases), Service: optionalString(raw, "service"), StartsAt: startsAt, EndsAt: endsAt, Severity: severity, AllowedOwners: plainStringSet(stringArray(raw["allowed_owners"])), Source: src}, nil, true
}

func filterEvents(deployments map[string]Deployment, probes []Probe, incidents []Incident, rollbacks []Rollback) ([]Probe, []Incident, []Rollback, []Warning) {
	usableProbes := []Probe{}
	usableIncidents := []Incident{}
	usableRollbacks := []Rollback{}
	warnings := []Warning{}

	for _, probe := range probes {
		target, ok := deployments[probe.DeploymentID]
		if !ok {
			warnings = append(warnings, Warning{Code: "unknown_probe_deployment", Severity: "warning", SubjectID: probe.ID, SourcePath: probe.Source.Path, SourceLine: probe.Source.Line, Detail: fmt.Sprintf("probe %s references unknown deployment %s", probe.ID, probe.DeploymentID)})
			continue
		}
		if (probe.Service != "" && probe.Service != target.Service) || (probe.Environment != "" && probe.Environment != target.Environment) {
			targetService := probe.Service
			if targetService == "" {
				targetService = target.Service
			}
			targetEnvironment := probe.Environment
			if targetEnvironment == "" {
				targetEnvironment = target.Environment
			}
			warnings = append(warnings, Warning{Code: "probe_service_mismatch", Severity: "warning", SubjectID: probe.ID, SourcePath: probe.Source.Path, SourceLine: probe.Source.Line, Detail: fmt.Sprintf("probe %s targets %s/%s but deployment %s is %s/%s", probe.ID, targetService, targetEnvironment, target.ID, target.Service, target.Environment)})
			continue
		}
		usableProbes = append(usableProbes, probe)
	}

	for _, incident := range incidents {
		if _, ok := deployments[incident.DeploymentID]; !ok {
			warnings = append(warnings, Warning{Code: "unknown_incident_deployment", Severity: "warning", SubjectID: incident.ID, SourcePath: incident.Source.Path, SourceLine: incident.Source.Line, Detail: fmt.Sprintf("incident %s references unknown deployment %s", incident.ID, incident.DeploymentID)})
			continue
		}
		usableIncidents = append(usableIncidents, incident)
	}

	for _, rollback := range rollbacks {
		if _, ok := deployments[rollback.DeploymentID]; !ok {
			warnings = append(warnings, Warning{Code: "unknown_rollback_deployment", Severity: "warning", SubjectID: rollback.ID, SourcePath: rollback.Source.Path, SourceLine: rollback.Source.Line, Detail: fmt.Sprintf("rollback %s references unknown deployment %s", rollback.ID, rollback.DeploymentID)})
			continue
		}
		usableRollbacks = append(usableRollbacks, rollback)
	}

	return usableProbes, usableIncidents, usableRollbacks, warnings
}

func buildWindow(dep Deployment, probes []Probe, incidents []Incident, rollbacks []Rollback, cfg Config) (Window, []Warning) {
	warnings := []Warning{}
	windowStart := dep.StartedAt
	windowEnd := dep.StartedAt.Add(time.Duration(dep.DurationMins) * time.Minute)
	graceEnd := windowEnd.Add(time.Duration(cfg.RollbackGraceMinutes) * time.Minute)

	matchedProbes := []Probe{}
	for _, probe := range probes {
		if probe.DeploymentID != dep.ID {
			continue
		}
		if !probe.CheckedAt.Before(windowStart) && !probe.CheckedAt.After(windowEnd) {
			matchedProbes = append(matchedProbes, probe)
		}
	}
	sort.Slice(matchedProbes, func(i, j int) bool {
		if !matchedProbes[i].CheckedAt.Equal(matchedProbes[j].CheckedAt) {
			return matchedProbes[i].CheckedAt.Before(matchedProbes[j].CheckedAt)
		}
		return matchedProbes[i].ID < matchedProbes[j].ID
	})

	observedIDs := []string{}
	failedIDs := []string{}
	passedTypes := map[string]bool{}
	for _, probe := range matchedProbes {
		observedIDs = append(observedIDs, probe.ID)
		if probe.Status == "fail" {
			failedIDs = append(failedIDs, probe.ID)
		} else if probe.Status == "pass" {
			passedTypes[probe.Type] = true
		}
	}

	missingTypes := []string{}
	for _, probeType := range dep.RequiredTypes {
		if !passedTypes[probeType] {
			missingTypes = append(missingTypes, probeType)
		}
	}

	matchedIncidents := []Incident{}
	for _, incident := range incidents {
		if incident.DeploymentID != dep.ID || (incident.Severity != "critical" && incident.Severity != "major") {
			continue
		}
		if !incident.StartedAt.After(windowEnd) && (incident.EndedAt == nil || !incident.EndedAt.Before(windowStart)) {
			matchedIncidents = append(matchedIncidents, incident)
		}
	}
	sort.Slice(matchedIncidents, func(i, j int) bool {
		if !matchedIncidents[i].StartedAt.Equal(matchedIncidents[j].StartedAt) {
			return matchedIncidents[i].StartedAt.Before(matchedIncidents[j].StartedAt)
		}
		return matchedIncidents[i].ID < matchedIncidents[j].ID
	})
	incidentIDs := []string{}
	hasCritical := false
	hasMajor := false
	for _, incident := range matchedIncidents {
		incidentIDs = append(incidentIDs, incident.ID)
		if incident.Severity == "critical" {
			hasCritical = true
		}
		if incident.Severity == "major" {
			hasMajor = true
		}
	}

	effective := []Rollback{}
	for _, rollback := range rollbacks {
		if rollback.DeploymentID != dep.ID || rollback.State != "applied" {
			continue
		}
		if rollback.MarkedAt.Before(windowStart) {
			continue
		}
		if rollback.MarkedAt.After(graceEnd) {
			warnings = append(warnings, Warning{Code: "late_rollback", Severity: "warning", SubjectID: rollback.ID, SourcePath: rollback.Source.Path, SourceLine: rollback.Source.Line, Detail: fmt.Sprintf("rollback %s marked after grace window for deployment %s", rollback.ID, rollback.DeploymentID)})
			continue
		}
		effective = append(effective, rollback)
	}
	sort.Slice(effective, func(i, j int) bool {
		if !effective[i].MarkedAt.Equal(effective[j].MarkedAt) {
			return effective[i].MarkedAt.Before(effective[j].MarkedAt)
		}
		return effective[i].ID < effective[j].ID
	})

	healthState := "healthy"
	var rollbackID *string
	var rollbackAt *string
	if len(effective) > 0 {
		id := effective[0].ID
		marked := formatTime(effective[0].MarkedAt)
		rollbackID = &id
		rollbackAt = &marked
		healthState = "rolled_back"
	} else if len(failedIDs) > 0 || hasCritical {
		healthState = "failed"
	} else if len(missingTypes) > 0 || hasMajor {
		healthState = "degraded"
	}

	return Window{
		DeploymentID: dep.ID, Service: dep.Service, Environment: dep.Environment,
		ReleaseID: dep.ReleaseID, Owner: dep.Owner, WindowStart: formatTime(windowStart), WindowEnd: formatTime(windowEnd),
		DurationMinutes: dep.DurationMins, RequiredProbeTypes: append([]string{}, dep.RequiredTypes...),
		ObservedProbeIDs: observedIDs, MissingProbeTypes: missingTypes, FailedProbeIDs: failedIDs,
		IncidentIDs: incidentIDs, DependsOn: append([]string{}, dep.DependsOn...), FreezeWindowIDs: []string{}, PolicyViolationCodes: []string{}, BaseHealthState: healthState,
		BlockedByDeploymentIDs: []string{}, RollbackMarkerID: rollbackID, RollbackEffectiveAt: rollbackAt, HealthState: healthState,
	}, warnings
}

func applyFreezeOverlay(windows []Window, deployments map[string]Deployment, freezes []Freeze) {
	for idx := range windows {
		windowStart, _ := parseTimestamp(windows[idx].WindowStart)
		windowEnd, _ := parseTimestamp(windows[idx].WindowEnd)
		dep := deployments[windows[idx].DeploymentID]
		matched := []Freeze{}
		for _, freeze := range freezes {
			if freeze.Environment != windows[idx].Environment {
				continue
			}
			if freeze.Service != "" && freeze.Service != windows[idx].Service {
				continue
			}
			if freeze.StartsAt.After(windowEnd) || freeze.EndsAt.Before(windowStart) {
				continue
			}
			matched = append(matched, freeze)
		}
		sort.Slice(matched, func(i, j int) bool {
			if !matched[i].StartsAt.Equal(matched[j].StartsAt) {
				return matched[i].StartsAt.Before(matched[j].StartsAt)
			}
			return matched[i].ID < matched[j].ID
		})
		freezeIDs := []string{}
		violationSet := map[string]bool{}
		for _, freeze := range matched {
			freezeIDs = append(freezeIDs, freeze.ID)
			if freeze.Severity != "hard" || ownerAllowed(dep.Owner, freeze.AllowedOwners) {
				continue
			}
			violationSet["hard_freeze_overlap"] = true
			if windows[idx].RollbackEffectiveAt != nil {
				rollbackAt, err := parseTimestamp(*windows[idx].RollbackEffectiveAt)
				if err == nil && !rollbackAt.Before(freeze.StartsAt) && !rollbackAt.After(freeze.EndsAt) {
					violationSet["rollback_during_freeze"] = true
				}
			}
		}
		codes := make([]string, 0, len(violationSet))
		for code := range violationSet {
			codes = append(codes, code)
		}
		sort.Strings(codes)
		windows[idx].FreezeWindowIDs = freezeIDs
		windows[idx].PolicyViolationCodes = codes
		if (windows[idx].HealthState == "healthy" || windows[idx].HealthState == "degraded") && violationSet["hard_freeze_overlap"] {
			windows[idx].HealthState = "frozen"
		}
	}
}

func ownerAllowed(owner string, allowed []string) bool {
	if len(allowed) == 0 {
		return false
	}
	trimmed := strings.TrimSpace(owner)
	for _, candidate := range allowed {
		if trimmed == candidate {
			return true
		}
	}
	return false
}

func applyDependencyOverlay(windows []Window, deployments map[string]Deployment) []Warning {
	warnings := []Warning{}
	indexByID := map[string]int{}
	for idx := range windows {
		indexByID[windows[idx].DeploymentID] = idx
	}

	knownDeps := map[string][]string{}
	for id, dep := range deployments {
		deps := []string{}
		for _, depID := range dep.DependsOn {
			if _, ok := deployments[depID]; ok {
				deps = append(deps, depID)
			} else {
				warnings = append(warnings, Warning{
					Code:       "unknown_dependency",
					Severity:   "warning",
					SubjectID:  dep.ID,
					SourcePath: dep.Source.Path,
					SourceLine: dep.Source.Line,
					Detail:     fmt.Sprintf("deployment %s depends on unknown deployment %s", dep.ID, depID),
				})
			}
		}
		knownDeps[id] = deps
	}

	cycleMembers, cycleLists := dependencyCycles(knownDeps)
	for id, members := range cycleLists {
		dep := deployments[id]
		warnings = append(warnings, Warning{
			Code:       "dependency_cycle",
			Severity:   "warning",
			SubjectID:  id,
			SourcePath: dep.Source.Path,
			SourceLine: dep.Source.Line,
			Detail:     fmt.Sprintf("deployment %s participates in dependency cycle %s", id, strings.Join(members, ",")),
		})
	}

	for pass := 0; pass < len(windows); pass++ {
		changed := false
		for idx := range windows {
			id := windows[idx].DeploymentID
			windows[idx].BlockedByDeploymentIDs = []string{}
			if cycleMembers[id] || (windows[idx].BaseHealthState != "healthy" && windows[idx].BaseHealthState != "degraded") {
				windows[idx].HealthState = windows[idx].BaseHealthState
				continue
			}
			blockedBy := []string{}
			for _, depID := range knownDeps[id] {
				if cycleMembers[depID] {
					continue
				}
				depIdx, ok := indexByID[depID]
				if !ok {
					continue
				}
				state := windows[depIdx].HealthState
				if state == "failed" || state == "rolled_back" || state == "blocked" {
					blockedBy = append(blockedBy, depID)
				}
			}
			sort.Strings(blockedBy)
			newState := windows[idx].BaseHealthState
			if len(blockedBy) > 0 {
				newState = "blocked"
			}
			if windows[idx].HealthState != newState {
				changed = true
			}
			windows[idx].HealthState = newState
			windows[idx].BlockedByDeploymentIDs = blockedBy
		}
		if !changed {
			break
		}
	}

	return warnings
}

func dependencyCycles(graph map[string][]string) (map[string]bool, map[string][]string) {
	index := 0
	indices := map[string]int{}
	lowlink := map[string]int{}
	stack := []string{}
	onStack := map[string]bool{}
	cycleMembers := map[string]bool{}
	cycleLists := map[string][]string{}

	var strongConnect func(string)
	strongConnect = func(v string) {
		indices[v] = index
		lowlink[v] = index
		index++
		stack = append(stack, v)
		onStack[v] = true

		for _, w := range graph[v] {
			if _, seen := indices[w]; !seen {
				strongConnect(w)
				if lowlink[w] < lowlink[v] {
					lowlink[v] = lowlink[w]
				}
			} else if onStack[w] && indices[w] < lowlink[v] {
				lowlink[v] = indices[w]
			}
		}

		if lowlink[v] == indices[v] {
			scc := []string{}
			for {
				last := stack[len(stack)-1]
				stack = stack[:len(stack)-1]
				onStack[last] = false
				scc = append(scc, last)
				if last == v {
					break
				}
			}
			selfLoop := false
			if len(scc) == 1 {
				for _, dep := range graph[scc[0]] {
					if dep == scc[0] {
						selfLoop = true
					}
				}
			}
			if len(scc) > 1 || selfLoop {
				sort.Strings(scc)
				for _, member := range scc {
					cycleMembers[member] = true
					cycleLists[member] = append([]string{}, scc...)
				}
			}
		}
	}

	ids := make([]string, 0, len(graph))
	for id := range graph {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	for _, id := range ids {
		if _, seen := indices[id]; !seen {
			strongConnect(id)
		}
	}
	return cycleMembers, cycleLists
}

func duplicateWarning(discarded Deployment, kept Deployment) Warning {
	return Warning{Code: "duplicate_deployment", Severity: "warning", SubjectID: discarded.ID, SourcePath: discarded.Source.Path, SourceLine: discarded.Source.Line, Detail: fmt.Sprintf("duplicate deployment %s; kept %s:%d", discarded.ID, kept.Source.Path, kept.Source.Line)}
}

func deploymentWins(candidate Deployment, incumbent Deployment) bool {
	if candidate.Priority != incumbent.Priority {
		return candidate.Priority > incumbent.Priority
	}
	if !candidate.StartedAt.Equal(incumbent.StartedAt) {
		return candidate.StartedAt.After(incumbent.StartedAt)
	}
	if candidate.Source.Path != incumbent.Source.Path {
		return candidate.Source.Path < incumbent.Source.Path
	}
	return candidate.Source.Line < incumbent.Source.Line
}

func invalidWarning(recordType, id string, src Source, reason string) *Warning {
	code := "invalid_" + recordType
	return &Warning{Code: code, Severity: "error", SubjectID: id, SourcePath: src.Path, SourceLine: src.Line, Detail: fmt.Sprintf("invalid %s %s: %s", recordType, id, reason)}
}

func parseTimestamp(raw string) (time.Time, error) {
	if strings.TrimSpace(raw) == "" {
		return time.Time{}, errors.New("empty timestamp")
	}
	parsed, err := time.Parse(time.RFC3339, raw)
	if err != nil {
		return time.Time{}, err
	}
	return parsed.UTC(), nil
}

func formatTime(t time.Time) string {
	return t.UTC().Format(time.RFC3339)
}

func canonical(raw string, aliases map[string]string) string {
	key := strings.ToLower(strings.TrimSpace(raw))
	if aliases == nil {
		return key
	}
	if value, ok := aliases[key]; ok {
		return value
	}
	return key
}

func canonicalStringSet(values []string, aliases map[string]string) []string {
	seen := map[string]bool{}
	result := []string{}
	for _, raw := range values {
		canonicalValue := canonical(raw, aliases)
		if canonicalValue == "" || seen[canonicalValue] {
			continue
		}
		seen[canonicalValue] = true
		result = append(result, canonicalValue)
	}
	sort.Strings(result)
	return result
}

func plainStringSet(values []string) []string {
	seen := map[string]bool{}
	result := []string{}
	for _, raw := range values {
		value := strings.TrimSpace(raw)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		result = append(result, value)
	}
	sort.Strings(result)
	return result
}

func optionalString(raw map[string]any, field string) string {
	value, ok := raw[field]
	if !ok || value == nil {
		return ""
	}
	str, ok := value.(string)
	if !ok {
		return ""
	}
	return strings.TrimSpace(str)
}

func intValue(value any) (int, error) {
	number, ok := value.(float64)
	if !ok || number != float64(int(number)) {
		return 0, errors.New("not an integer")
	}
	return int(number), nil
}

func stringArray(value any) []string {
	if value == nil {
		return nil
	}
	array, ok := value.([]any)
	if !ok {
		return nil
	}
	result := []string{}
	for _, item := range array {
		if str, ok := item.(string); ok {
			result = append(result, str)
		}
	}
	return result
}

func sortWarnings(warnings []Warning) {
	sort.Slice(warnings, func(i, j int) bool {
		a := warnings[i]
		b := warnings[j]
		if a.Code != b.Code {
			return a.Code < b.Code
		}
		if a.SubjectID != b.SubjectID {
			return a.SubjectID < b.SubjectID
		}
		if a.SourcePath != b.SourcePath {
			return a.SourcePath < b.SourcePath
		}
		if a.SourceLine != b.SourceLine {
			return a.SourceLine < b.SourceLine
		}
		return a.Detail < b.Detail
	})
}

func prepareOutput(out string) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	entries, err := os.ReadDir(out)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		if !entry.IsDir() && strings.HasSuffix(entry.Name(), ".json") {
			if err := os.Remove(filepath.Join(out, entry.Name())); err != nil {
				return err
			}
		}
	}
	return nil
}

func writeJSON(path string, value any) error {
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	return os.WriteFile(path, data, 0o644)
}
GO

gofmt -w /app/cmd/reconciler/main.go
go test ./...
/app/bin/reconcile-health-windows --config /app/config/health-window-policy.json --input /app/fixtures --out /app/out
