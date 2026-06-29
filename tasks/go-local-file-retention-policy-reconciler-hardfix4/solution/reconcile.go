package src

import (
	"bufio"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io/fs"
	"os"
	posixpath "path"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

type configFile struct {
	EvaluationTime      string                 `json:"evaluation_time"`
	Defaults            policyDefaults         `json:"defaults"`
	Classes             map[string]classPolicy `json:"classes"`
	ClassAliases        map[string]string      `json:"class_aliases"`
	Exceptions          []exceptionWindow      `json:"exceptions"`
	CleanupBlocks       []cleanupBlock         `json:"cleanup_blocks"`
	CleanupCapacity     map[string]int         `json:"cleanup_capacity"`
	CleanupByteCapacity map[string]int64       `json:"cleanup_byte_capacity"`
}

type policyDefaults struct {
	RetentionDays int    `json:"retention_days"`
	MaxMode       string `json:"max_mode"`
	DeleteAction  string `json:"delete_action"`
}

type classPolicy struct {
	PolicyID      string `json:"policy_id"`
	RetentionDays int    `json:"retention_days"`
	MaxMode       string `json:"max_mode"`
	DeleteAction  string `json:"delete_action"`
}

type exceptionWindow struct {
	ExceptionID   string `json:"exception_id"`
	PathPrefix    string `json:"path_prefix"`
	Class         string `json:"class"`
	StartsAt      string `json:"starts_at"`
	EndsAt        string `json:"ends_at"`
	RetentionDays int    `json:"retention_days"`
	AllowMode     bool   `json:"allow_mode"`

	startTime time.Time
	endTime   time.Time
	prefix    string
}

type cleanupBlock struct {
	BlockerID  string   `json:"blocker_id"`
	PathPrefix string   `json:"path_prefix"`
	Class      string   `json:"class"`
	StartsAt   string   `json:"starts_at"`
	EndsAt     string   `json:"ends_at"`
	AppliesTo  []string `json:"applies_to"`

	startTime time.Time
	endTime   time.Time
	prefix    string
}

type rawRecord struct {
	Path           string   `json:"path"`
	RecordType     string   `json:"record_type"`
	Class          string   `json:"class"`
	ModifiedAt     string   `json:"modified_at"`
	Mode           string   `json:"mode"`
	Owner          string   `json:"owner"`
	Group          string   `json:"group"`
	RetentionGroup string   `json:"retention_group"`
	CleanupAfter   []string `json:"cleanup_after"`
	SizeBytes      int64    `json:"size_bytes"`
	SourceRank     int      `json:"source_rank"`
	ScannedAt      string   `json:"scanned_at"`
}

type candidate struct {
	raw          rawRecord
	path         string
	modifiedTime time.Time
	scannedTime  time.Time
	sourcePath   string
	sourceLine   int
	cleanupAfter []string
}

type warningRow struct {
	Code        string `json:"code"`
	Severity    string `json:"severity"`
	SubjectPath string `json:"subject_path"`
	SourcePath  string `json:"source_path"`
	SourceLine  int    `json:"source_line"`
	Detail      string `json:"detail"`
}

type reportRecord struct {
	Path              string  `json:"path"`
	Class             string  `json:"class"`
	PolicyID          string  `json:"policy_id"`
	Owner             string  `json:"owner"`
	Group             string  `json:"group"`
	RetentionGroup    string  `json:"retention_group"`
	Mode              string  `json:"mode"`
	SizeBytes         int64   `json:"size_bytes"`
	SourcePath        string  `json:"source_path"`
	SourceLine        int     `json:"source_line"`
	ModifiedAt        string  `json:"modified_at"`
	AgeDays           int     `json:"age_days"`
	BaseDeadline      *string `json:"base_deadline"`
	EffectiveDeadline *string `json:"effective_deadline"`
	ExceptionID       string  `json:"exception_id"`
	BlockedBy         string  `json:"blocked_by"`
	ModeCompliant     bool    `json:"mode_compliant"`
	Status            string  `json:"status"`
}

type summary struct {
	RecordsTotal    int              `json:"records_total"`
	ActionsTotal    int              `json:"actions_total"`
	WarningsTotal   int              `json:"warnings_total"`
	RecordsByStatus map[string]int   `json:"records_by_status"`
	BytesByStatus   map[string]int64 `json:"bytes_by_status"`
}

type retentionReport struct {
	GeneratedAt string         `json:"generated_at"`
	Summary     summary        `json:"summary"`
	Records     []reportRecord `json:"records"`
}

type actionRow struct {
	Wave        int      `json:"wave"`
	Action      string   `json:"action"`
	Path        string   `json:"path"`
	PolicyID    string   `json:"policy_id"`
	ExceptionID string   `json:"exception_id"`
	ReasonCodes []string `json:"reason_codes"`
	DueAt       string   `json:"due_at"`
	SourcePath  string   `json:"source_path"`
	SourceLine  int      `json:"source_line"`
}

type cleanupPlan struct {
	GeneratedAt string      `json:"generated_at"`
	Actions     []actionRow `json:"actions"`
}

type warningsFile struct {
	GeneratedAt string       `json:"generated_at"`
	Warnings    []warningRow `json:"warnings"`
}

var modeRE = regexp.MustCompile(`^0[0-7]{3}$`)

func Run(args []string) error {
	fs := flag.NewFlagSet("local-retention-reconciler", flag.ContinueOnError)
	configPath := fs.String("config", "/app/config/retention-policy.json", "policy config")
	manifestsPath := fs.String("manifests", "/app/manifests", "manifest root")
	outDir := fs.String("out", "/app/out", "output directory")
	if err := fs.Parse(args); err != nil {
		return err
	}

	cfg, evaluationTime, err := loadConfig(*configPath)
	if err != nil {
		return err
	}

	candidates, warnings, err := loadCandidates(*manifestsPath)
	if err != nil {
		return err
	}
	kept, duplicateWarnings := resolveDuplicates(candidates)
	warnings = append(warnings, duplicateWarnings...)

	records, actions, policyWarnings := evaluateRecords(kept, cfg, evaluationTime)
	warnings = append(warnings, policyWarnings...)

	sort.Slice(records, func(i, j int) bool { return records[i].Path < records[j].Path })
	sort.Slice(actions, func(i, j int) bool {
		if actions[i].Wave != actions[j].Wave {
			return actions[i].Wave < actions[j].Wave
		}
		if actions[i].Action != actions[j].Action {
			return actions[i].Action < actions[j].Action
		}
		if actions[i].Path != actions[j].Path {
			return actions[i].Path < actions[j].Path
		}
		if actions[i].SourcePath != actions[j].SourcePath {
			return actions[i].SourcePath < actions[j].SourcePath
		}
		return actions[i].SourceLine < actions[j].SourceLine
	})
	sortWarnings(warnings)

	generatedAt := formatTime(evaluationTime)
	report := retentionReport{
		GeneratedAt: generatedAt,
		Summary: summary{
			RecordsTotal:    len(records),
			ActionsTotal:    len(actions),
			WarningsTotal:   len(warnings),
			RecordsByStatus: map[string]int{},
			BytesByStatus:   map[string]int64{},
		},
		Records: records,
	}
	for _, record := range records {
		report.Summary.RecordsByStatus[record.Status]++
		report.Summary.BytesByStatus[record.Status] += record.SizeBytes
	}

	if err := prepareOutDir(*outDir); err != nil {
		return err
	}
	if err := writeJSON(filepath.Join(*outDir, "retention_report.json"), report); err != nil {
		return err
	}
	if err := writeJSON(filepath.Join(*outDir, "cleanup_plan.json"), cleanupPlan{GeneratedAt: generatedAt, Actions: actions}); err != nil {
		return err
	}
	return writeJSON(filepath.Join(*outDir, "warnings.json"), warningsFile{GeneratedAt: generatedAt, Warnings: warnings})
}

func loadConfig(path string) (*configFile, time.Time, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, time.Time{}, err
	}
	var cfg configFile
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, time.Time{}, err
	}
	evaluationTime, err := time.Parse(time.RFC3339, cfg.EvaluationTime)
	if err != nil {
		return nil, time.Time{}, fmt.Errorf("evaluation_time must be RFC3339: %w", err)
	}
	if cfg.Classes == nil {
		cfg.Classes = map[string]classPolicy{}
	}
	if cfg.ClassAliases == nil {
		cfg.ClassAliases = map[string]string{}
	}
	if cfg.CleanupCapacity == nil {
		cfg.CleanupCapacity = map[string]int{}
	}
	if cfg.CleanupByteCapacity == nil {
		cfg.CleanupByteCapacity = map[string]int64{}
	}
	if cfg.Defaults.DeleteAction == "" {
		cfg.Defaults.DeleteAction = "delete"
	}
	for className, policy := range cfg.Classes {
		if policy.PolicyID == "" {
			policy.PolicyID = className
		}
		if policy.RetentionDays == 0 {
			policy.RetentionDays = cfg.Defaults.RetentionDays
		}
		if policy.MaxMode == "" {
			policy.MaxMode = cfg.Defaults.MaxMode
		}
		if policy.DeleteAction == "" {
			policy.DeleteAction = cfg.Defaults.DeleteAction
		}
		cfg.Classes[className] = policy
	}
	for idx := range cfg.Exceptions {
		ex := &cfg.Exceptions[idx]
		ex.prefix = normalizePrefix(ex.PathPrefix)
		ex.startTime, err = time.Parse(time.RFC3339, ex.StartsAt)
		if err != nil {
			return nil, time.Time{}, fmt.Errorf("exception %s starts_at must be RFC3339: %w", ex.ExceptionID, err)
		}
		ex.endTime, err = time.Parse(time.RFC3339, ex.EndsAt)
		if err != nil {
			return nil, time.Time{}, fmt.Errorf("exception %s ends_at must be RFC3339: %w", ex.ExceptionID, err)
		}
	}
	for idx := range cfg.CleanupBlocks {
		block := &cfg.CleanupBlocks[idx]
		block.prefix = normalizePrefix(block.PathPrefix)
		block.startTime, err = time.Parse(time.RFC3339, block.StartsAt)
		if err != nil {
			return nil, time.Time{}, fmt.Errorf("cleanup block %s starts_at must be RFC3339: %w", block.BlockerID, err)
		}
		block.endTime, err = time.Parse(time.RFC3339, block.EndsAt)
		if err != nil {
			return nil, time.Time{}, fmt.Errorf("cleanup block %s ends_at must be RFC3339: %w", block.BlockerID, err)
		}
	}
	return &cfg, evaluationTime.UTC(), nil
}

func loadCandidates(root string) ([]candidate, []warningRow, error) {
	manifestPaths := []string{}
	if err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		if strings.HasSuffix(d.Name(), ".jsonl") {
			manifestPaths = append(manifestPaths, filepath.ToSlash(path))
		}
		return nil
	}); err != nil {
		return nil, nil, err
	}
	sort.Strings(manifestPaths)

	candidates := []candidate{}
	warnings := []warningRow{}
	for _, manifestPath := range manifestPaths {
		file, err := os.Open(manifestPath)
		if err != nil {
			return nil, nil, err
		}
		scanner := bufio.NewScanner(file)
		lineNo := 0
		for scanner.Scan() {
			lineNo++
			line := strings.TrimSpace(scanner.Text())
			if line == "" {
				continue
			}
			var raw rawRecord
			if err := json.Unmarshal([]byte(line), &raw); err != nil {
				warnings = append(warnings, warningRow{
					Code:        "malformed_manifest",
					Severity:    "error",
					SubjectPath: "",
					SourcePath:  manifestPath,
					SourceLine:  lineNo,
					Detail:      fmt.Sprintf("malformed JSON at %s:%d", manifestPath, lineNo),
				})
				continue
			}
			cand, reason := validateRecord(raw, manifestPath, lineNo)
			if reason != "" {
				subject := ""
				if strings.HasPrefix(raw.Path, "/") {
					subject = normalizePath(raw.Path)
				}
				warnings = append(warnings, warningRow{
					Code:        "invalid_manifest",
					Severity:    "error",
					SubjectPath: subject,
					SourcePath:  manifestPath,
					SourceLine:  lineNo,
					Detail:      "invalid manifest record: " + reason,
				})
				continue
			}
			candidates = append(candidates, cand)
		}
		if err := scanner.Err(); err != nil {
			closeErr := file.Close()
			if closeErr != nil {
				return nil, nil, errors.Join(err, closeErr)
			}
			return nil, nil, err
		}
		if err := file.Close(); err != nil {
			return nil, nil, err
		}
	}
	return candidates, warnings, nil
}

func validateRecord(raw rawRecord, sourcePath string, sourceLine int) (candidate, string) {
	if !strings.HasPrefix(raw.Path, "/") {
		return candidate{}, "path must be absolute"
	}
	if raw.RecordType != "file" {
		return candidate{}, "record_type must be file"
	}
	if strings.TrimSpace(raw.Class) == "" {
		return candidate{}, "class is required"
	}
	if strings.TrimSpace(raw.ModifiedAt) == "" {
		return candidate{}, "modified_at is required"
	}
	modifiedTime, err := time.Parse(time.RFC3339, raw.ModifiedAt)
	if err != nil {
		return candidate{}, "modified_at must be RFC3339"
	}
	if !modeRE.MatchString(raw.Mode) {
		return candidate{}, "mode must be four octal digits"
	}
	if raw.SizeBytes < 0 {
		return candidate{}, "size_bytes must be non-negative"
	}
	scannedTime := time.Time{}
	if strings.TrimSpace(raw.ScannedAt) != "" {
		scannedTime, err = time.Parse(time.RFC3339, raw.ScannedAt)
		if err != nil {
			scannedTime = time.Time{}
		}
	}
	return candidate{
		raw:          raw,
		path:         normalizePath(raw.Path),
		modifiedTime: modifiedTime.UTC(),
		scannedTime:  scannedTime.UTC(),
		sourcePath:   filepath.ToSlash(sourcePath),
		sourceLine:   sourceLine,
		cleanupAfter: normalizeDependencyPaths(raw.CleanupAfter),
	}, ""
}

func resolveDuplicates(candidates []candidate) ([]candidate, []warningRow) {
	byPath := map[string]candidate{}
	duplicates := []candidate{}
	for _, cand := range candidates {
		kept, exists := byPath[cand.path]
		if !exists {
			byPath[cand.path] = cand
			continue
		}
		if candidateBeats(cand, kept) {
			duplicates = append(duplicates, kept)
			byPath[cand.path] = cand
		} else {
			duplicates = append(duplicates, cand)
		}
	}
	kept := make([]candidate, 0, len(byPath))
	for _, cand := range byPath {
		kept = append(kept, cand)
	}
	sort.Slice(kept, func(i, j int) bool { return kept[i].path < kept[j].path })

	warnings := []warningRow{}
	for _, discarded := range duplicates {
		winner := byPath[discarded.path]
		warnings = append(warnings, warningRow{
			Code:        "duplicate_manifest",
			Severity:    "warning",
			SubjectPath: discarded.path,
			SourcePath:  discarded.sourcePath,
			SourceLine:  discarded.sourceLine,
			Detail:      fmt.Sprintf("duplicate path %s; kept %s:%d", discarded.path, winner.sourcePath, winner.sourceLine),
		})
	}
	return kept, warnings
}

func candidateBeats(a, b candidate) bool {
	if a.raw.SourceRank != b.raw.SourceRank {
		return a.raw.SourceRank > b.raw.SourceRank
	}
	if !a.scannedTime.Equal(b.scannedTime) {
		return a.scannedTime.After(b.scannedTime)
	}
	if a.sourcePath != b.sourcePath {
		return a.sourcePath < b.sourcePath
	}
	return a.sourceLine < b.sourceLine
}

func evaluateRecords(candidates []candidate, cfg *configFile, evaluationTime time.Time) ([]reportRecord, []actionRow, []warningRow) {
	records := []reportRecord{}
	actions := []actionRow{}
	warnings := []warningRow{}
	cleanupAfterByPath := map[string][]string{}
	generatedAt := formatTime(evaluationTime)

	for _, cand := range candidates {
		cleanupAfterByPath[cand.path] = cand.cleanupAfter
		className := resolveClass(cfg, cand.raw.Class)
		policy, known := cfg.Classes[className]
		ageDays := wholeDays(cand.modifiedTime, evaluationTime)
		if !known {
			warnings = append(warnings, warningRow{
				Code:        "unknown_class",
				Severity:    "error",
				SubjectPath: cand.path,
				SourcePath:  cand.sourcePath,
				SourceLine:  cand.sourceLine,
				Detail:      "unknown class " + className,
			})
			records = append(records, reportRecord{
				Path:              cand.path,
				Class:             className,
				PolicyID:          "",
				Owner:             cand.raw.Owner,
				Group:             cand.raw.Group,
				RetentionGroup:    strings.TrimSpace(cand.raw.RetentionGroup),
				Mode:              cand.raw.Mode,
				SizeBytes:         cand.raw.SizeBytes,
				SourcePath:        cand.sourcePath,
				SourceLine:        cand.sourceLine,
				ModifiedAt:        formatTime(cand.modifiedTime),
				AgeDays:           ageDays,
				BaseDeadline:      nil,
				EffectiveDeadline: nil,
				ExceptionID:       "",
				BlockedBy:         "",
				ModeCompliant:     false,
				Status:            "needs_review",
			})
			continue
		}

		for _, ex := range cfg.Exceptions {
			if exceptionMatches(ex, cand.path, className) && !evaluationTime.Before(ex.endTime) {
				warnings = append(warnings, warningRow{
					Code:        "expired_exception",
					Severity:    "warning",
					SubjectPath: cand.path,
					SourcePath:  cand.sourcePath,
					SourceLine:  cand.sourceLine,
					Detail:      fmt.Sprintf("expired exception %s ignored for %s", ex.ExceptionID, cand.path),
				})
			}
		}

		baseDeadlineTime := cand.modifiedTime.AddDate(0, 0, policy.RetentionDays).UTC()
		effectiveDays := policy.RetentionDays
		active := chooseActiveException(cfg.Exceptions, cand.path, className, evaluationTime)
		exceptionID := ""
		allowMode := false
		if active != nil {
			exceptionID = active.ExceptionID
			allowMode = active.AllowMode
			if active.RetentionDays > 0 {
				effectiveDays = active.RetentionDays
			}
		}
		effectiveDeadlineTime := cand.modifiedTime.AddDate(0, 0, effectiveDays).UTC()
		baseDeadline := formatTime(baseDeadlineTime)
		effectiveDeadline := formatTime(effectiveDeadlineTime)

		modeCompliant := true
		modeTooPermissive := false
		if !allowMode {
			modeCompliant = modeAllowed(cand.raw.Mode, policy.MaxMode)
			modeTooPermissive = !modeCompliant
		}
		if modeTooPermissive {
			warnings = append(warnings, warningRow{
				Code:        "mode_too_permissive",
				Severity:    "warning",
				SubjectPath: cand.path,
				SourcePath:  cand.sourcePath,
				SourceLine:  cand.sourceLine,
				Detail:      fmt.Sprintf("mode %s exceeds max %s", cand.raw.Mode, policy.MaxMode),
			})
		}

		expired := !evaluationTime.Before(effectiveDeadlineTime)
		status := "retained"
		action := ""
		reasons := []string{}
		dueAt := ""
		if expired {
			status = policy.DeleteAction + "_due"
			action = policy.DeleteAction
			reasons = append(reasons, "retention_expired")
			dueAt = effectiveDeadline
		}
		if modeTooPermissive {
			if expired {
				reasons = append(reasons, "mode_too_permissive")
			} else if policy.DeleteAction == "quarantine" {
				status = "quarantine_due"
				action = "quarantine"
				reasons = append(reasons, "mode_too_permissive")
				dueAt = generatedAt
			} else {
				status = "permission_review"
				action = "chmod"
				reasons = append(reasons, "mode_too_permissive")
				dueAt = generatedAt
			}
		}
		if status == "retained" && active != nil && effectiveDeadlineTime.After(baseDeadlineTime) {
			status = "exception_retained"
		}

		blockedBy := ""
		if action != "" {
			block := chooseCleanupBlock(cfg.CleanupBlocks, cand.path, className, evaluationTime, action)
			if block != nil {
				blockedBy = block.BlockerID
				status = "cleanup_blocked"
				warnings = append(warnings, warningRow{
					Code:        "cleanup_blocked",
					Severity:    "warning",
					SubjectPath: cand.path,
					SourcePath:  cand.sourcePath,
					SourceLine:  cand.sourceLine,
					Detail:      fmt.Sprintf("cleanup blocked by %s for %s; action %s", block.BlockerID, cand.path, action),
				})
				action = ""
			}
		}

		records = append(records, reportRecord{
			Path:              cand.path,
			Class:             className,
			PolicyID:          policy.PolicyID,
			Owner:             cand.raw.Owner,
			Group:             cand.raw.Group,
			RetentionGroup:    strings.TrimSpace(cand.raw.RetentionGroup),
			Mode:              cand.raw.Mode,
			SizeBytes:         cand.raw.SizeBytes,
			SourcePath:        cand.sourcePath,
			SourceLine:        cand.sourceLine,
			ModifiedAt:        formatTime(cand.modifiedTime),
			AgeDays:           ageDays,
			BaseDeadline:      &baseDeadline,
			EffectiveDeadline: &effectiveDeadline,
			ExceptionID:       exceptionID,
			BlockedBy:         blockedBy,
			ModeCompliant:     modeCompliant,
			Status:            status,
		})
		if action != "" {
			actions = append(actions, actionRow{
				Action:      action,
				Path:        cand.path,
				PolicyID:    policy.PolicyID,
				ExceptionID: exceptionID,
				ReasonCodes: reasons,
				DueAt:       dueAt,
				SourcePath:  cand.sourcePath,
				SourceLine:  cand.sourceLine,
			})
		}
	}
	var groupWarnings []warningRow
	records, actions, groupWarnings = applyRetentionGroupHolds(records, actions)
	warnings = append(warnings, groupWarnings...)
	var dependencyWarnings []warningRow
	records, actions, dependencyWarnings = applyCleanupDependenciesAndCapacity(records, actions, cleanupAfterByPath, cfg.CleanupCapacity, cfg.CleanupByteCapacity)
	warnings = append(warnings, dependencyWarnings...)
	return records, actions, warnings
}

func applyRetentionGroupHolds(records []reportRecord, actions []actionRow) ([]reportRecord, []actionRow, []warningRow) {
	protectors := map[string]string{}
	for _, record := range records {
		group := strings.TrimSpace(record.RetentionGroup)
		if group == "" {
			continue
		}
		if record.Status != "exception_retained" && record.Status != "cleanup_blocked" {
			continue
		}
		current, exists := protectors[group]
		if !exists || record.Path < current {
			protectors[group] = record.Path
		}
	}

	indexByPath := map[string]int{}
	for idx := range records {
		indexByPath[records[idx].Path] = idx
	}

	filteredActions := []actionRow{}
	warnings := []warningRow{}
	for _, action := range actions {
		idx, exists := indexByPath[action.Path]
		if !exists {
			filteredActions = append(filteredActions, action)
			continue
		}
		group := strings.TrimSpace(records[idx].RetentionGroup)
		protectorPath, protected := protectors[group]
		if group == "" || !protected || protectorPath == action.Path {
			filteredActions = append(filteredActions, action)
			continue
		}

		records[idx].Status = "group_blocked"
		records[idx].BlockedBy = fmt.Sprintf("group:%s:%s", group, protectorPath)
		warnings = append(warnings, warningRow{
			Code:        "group_blocked",
			Severity:    "warning",
			SubjectPath: action.Path,
			SourcePath:  action.SourcePath,
			SourceLine:  action.SourceLine,
			Detail:      fmt.Sprintf("group %s blocked %s for %s due to %s", group, action.Action, action.Path, protectorPath),
		})
	}
	return records, filteredActions, warnings
}

func applyCleanupDependenciesAndCapacity(records []reportRecord, actions []actionRow, cleanupAfterByPath map[string][]string, capacity map[string]int, byteCapacity map[string]int64) ([]reportRecord, []actionRow, []warningRow) {
	indexByPath := map[string]int{}
	sizeByPath := map[string]int64{}
	for idx := range records {
		indexByPath[records[idx].Path] = idx
		sizeByPath[records[idx].Path] = records[idx].SizeBytes
	}

	actionByPath := map[string]actionRow{}
	paths := make([]string, 0, len(actions))
	for _, action := range actions {
		actionByPath[action.Path] = action
		paths = append(paths, action.Path)
	}
	sort.Strings(paths)

	deps := map[string][]string{}
	for _, path := range paths {
		seen := map[string]bool{}
		for _, dep := range cleanupAfterByPath[path] {
			if _, ok := actionByPath[dep]; !ok {
				continue
			}
			if seen[dep] {
				continue
			}
			seen[dep] = true
			deps[path] = append(deps[path], dep)
		}
		sort.Strings(deps[path])
	}

	cycleGroups := dependencyCycleGroups(paths, deps)
	blockedByPath := map[string]string{}
	for _, group := range cycleGroups {
		if len(group) == 0 {
			continue
		}
		sort.Strings(group)
		anchor := group[0]
		for _, path := range group {
			blockedByPath[path] = anchor
		}
	}

	warnings := []warningRow{}
	remaining := []actionRow{}
	remainingByPath := map[string]bool{}
	for _, action := range actions {
		anchor, blocked := blockedByPath[action.Path]
		if !blocked {
			remaining = append(remaining, action)
			remainingByPath[action.Path] = true
			continue
		}
		if idx, ok := indexByPath[action.Path]; ok {
			records[idx].Status = "dependency_blocked"
			records[idx].BlockedBy = "cycle:" + anchor
		}
		warnings = append(warnings, warningRow{
			Code:        "dependency_cycle",
			Severity:    "error",
			SubjectPath: action.Path,
			SourcePath:  action.SourcePath,
			SourceLine:  action.SourceLine,
			Detail:      fmt.Sprintf("cleanup dependency cycle %s includes %s", anchor, action.Path),
		})
	}

	deps = map[string][]string{}
	for _, action := range remaining {
		for _, dep := range cleanupAfterByPath[action.Path] {
			if remainingByPath[dep] {
				deps[action.Path] = append(deps[action.Path], dep)
			}
		}
		sort.Strings(deps[action.Path])
	}

	return records, assignCleanupWaves(remaining, deps, capacity, byteCapacity, sizeByPath), warnings
}

func assignCleanupWaves(actions []actionRow, deps map[string][]string, capacity map[string]int, byteCapacity map[string]int64, sizeByPath map[string]int64) []actionRow {
	actionsByPath := map[string]actionRow{}
	unscheduled := map[string]bool{}
	for _, action := range actions {
		actionsByPath[action.Path] = action
		unscheduled[action.Path] = true
	}

	scheduledWave := map[string]int{}
	wave := 1
	for len(unscheduled) > 0 {
		available := []actionRow{}
		for path := range unscheduled {
			ready := true
			for _, dep := range deps[path] {
				if scheduledWave[dep] == 0 {
					ready = false
					break
				}
			}
			if ready {
				available = append(available, actionsByPath[path])
			}
		}
		sort.Slice(available, func(i, j int) bool { return actionLess(available[i], available[j]) })
		if len(available) == 0 {
			for path := range unscheduled {
				action := actionsByPath[path]
				action.Wave = wave
				actionsByPath[path] = action
				delete(unscheduled, path)
				scheduledWave[path] = wave
			}
			break
		}

		usedByAction := map[string]int{}
		usedBytesByAction := map[string]int64{}
		scheduledThisWave := []string{}
		for _, action := range available {
			limit := capacityLimit(capacity, action.Action, len(actions))
			if limit > 0 && usedByAction[action.Action] >= limit {
				continue
			}
			byteLimit := byteCapacityLimit(byteCapacity, action.Action)
			size := sizeByPath[action.Path]
			if byteLimit > 0 && usedBytesByAction[action.Action]+size > byteLimit {
				continue
			}
			usedByAction[action.Action]++
			usedBytesByAction[action.Action] += size
			action.Wave = wave
			actionsByPath[action.Path] = action
			scheduledThisWave = append(scheduledThisWave, action.Path)
		}
		if len(scheduledThisWave) == 0 {
			path := available[0].Path
			action := actionsByPath[path]
			action.Wave = wave
			actionsByPath[path] = action
			scheduledThisWave = append(scheduledThisWave, path)
		}
		for _, path := range scheduledThisWave {
			delete(unscheduled, path)
			scheduledWave[path] = wave
		}
		wave++
	}

	result := make([]actionRow, 0, len(actionsByPath))
	for _, action := range actionsByPath {
		if action.Wave == 0 {
			action.Wave = 1
		}
		result = append(result, action)
	}
	sort.Slice(result, func(i, j int) bool {
		if result[i].Wave != result[j].Wave {
			return result[i].Wave < result[j].Wave
		}
		return actionLess(result[i], result[j])
	})
	return result
}

func actionLess(a, b actionRow) bool {
	if a.Action != b.Action {
		return a.Action < b.Action
	}
	if a.Path != b.Path {
		return a.Path < b.Path
	}
	if a.SourcePath != b.SourcePath {
		return a.SourcePath < b.SourcePath
	}
	return a.SourceLine < b.SourceLine
}

func capacityLimit(capacity map[string]int, action string, total int) int {
	if capacity == nil {
		return total
	}
	limit := capacity[action]
	if limit <= 0 {
		return total
	}
	return limit
}

func byteCapacityLimit(capacity map[string]int64, action string) int64 {
	if capacity == nil {
		return 0
	}
	limit := capacity[action]
	if limit <= 0 {
		return 0
	}
	return limit
}

func dependencyCycleGroups(paths []string, deps map[string][]string) [][]string {
	index := 0
	stack := []string{}
	onStack := map[string]bool{}
	indices := map[string]int{}
	lowlink := map[string]int{}
	groups := [][]string{}

	var strongConnect func(string)
	strongConnect = func(path string) {
		indices[path] = index
		lowlink[path] = index
		index++
		stack = append(stack, path)
		onStack[path] = true

		for _, dep := range deps[path] {
			if _, seen := indices[dep]; !seen {
				strongConnect(dep)
				if lowlink[dep] < lowlink[path] {
					lowlink[path] = lowlink[dep]
				}
			} else if onStack[dep] && indices[dep] < lowlink[path] {
				lowlink[path] = indices[dep]
			}
		}

		if lowlink[path] != indices[path] {
			return
		}
		component := []string{}
		for {
			last := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			onStack[last] = false
			component = append(component, last)
			if last == path {
				break
			}
		}
		if len(component) > 1 || hasSelfDependency(component[0], deps) {
			groups = append(groups, component)
		}
	}

	for _, path := range paths {
		if _, seen := indices[path]; !seen {
			strongConnect(path)
		}
	}
	return groups
}

func hasSelfDependency(path string, deps map[string][]string) bool {
	for _, dep := range deps[path] {
		if dep == path {
			return true
		}
	}
	return false
}

func normalizeDependencyPaths(values []string) []string {
	seen := map[string]bool{}
	result := []string{}
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if !strings.HasPrefix(trimmed, "/") {
			continue
		}
		normalized := normalizePath(trimmed)
		if seen[normalized] {
			continue
		}
		seen[normalized] = true
		result = append(result, normalized)
	}
	sort.Strings(result)
	return result
}

func chooseActiveException(exceptions []exceptionWindow, recordPath string, className string, evaluationTime time.Time) *exceptionWindow {
	var chosen *exceptionWindow
	for idx := range exceptions {
		ex := &exceptions[idx]
		if !exceptionMatches(*ex, recordPath, className) {
			continue
		}
		if evaluationTime.Before(ex.startTime) || !evaluationTime.Before(ex.endTime) {
			continue
		}
		if chosen == nil || activeExceptionBeats(*ex, *chosen) {
			chosen = ex
		}
	}
	return chosen
}

func activeExceptionBeats(a, b exceptionWindow) bool {
	if len(a.prefix) != len(b.prefix) {
		return len(a.prefix) > len(b.prefix)
	}
	if !a.startTime.Equal(b.startTime) {
		return a.startTime.After(b.startTime)
	}
	return a.ExceptionID < b.ExceptionID
}

func exceptionMatches(ex exceptionWindow, recordPath string, className string) bool {
	if ex.Class != "" && ex.Class != className {
		return false
	}
	return strings.HasPrefix(recordPath, ex.prefix)
}

func resolveClass(cfg *configFile, className string) string {
	seen := map[string]bool{}
	current := className
	for {
		if seen[current] {
			return current
		}
		seen[current] = true
		next, ok := cfg.ClassAliases[current]
		if !ok || strings.TrimSpace(next) == "" {
			return current
		}
		current = next
	}
}

func chooseCleanupBlock(blocks []cleanupBlock, recordPath string, className string, evaluationTime time.Time, action string) *cleanupBlock {
	var chosen *cleanupBlock
	for idx := range blocks {
		block := &blocks[idx]
		if !cleanupBlockMatches(*block, recordPath, className, evaluationTime, action) {
			continue
		}
		if chosen == nil || cleanupBlockBeats(*block, *chosen) {
			chosen = block
		}
	}
	return chosen
}

func cleanupBlockMatches(block cleanupBlock, recordPath string, className string, evaluationTime time.Time, action string) bool {
	if block.Class != "" && block.Class != className {
		return false
	}
	if !strings.HasPrefix(recordPath, block.prefix) {
		return false
	}
	if evaluationTime.Before(block.startTime) || !evaluationTime.Before(block.endTime) {
		return false
	}
	if len(block.AppliesTo) == 0 {
		return true
	}
	for _, allowed := range block.AppliesTo {
		if allowed == action {
			return true
		}
	}
	return false
}

func cleanupBlockBeats(a, b cleanupBlock) bool {
	if len(a.prefix) != len(b.prefix) {
		return len(a.prefix) > len(b.prefix)
	}
	if !a.startTime.Equal(b.startTime) {
		return a.startTime.After(b.startTime)
	}
	return a.BlockerID < b.BlockerID
}

func normalizePath(value string) string {
	cleaned := posixpath.Clean("/" + strings.TrimPrefix(value, "/"))
	if cleaned == "." {
		return "/"
	}
	return cleaned
}

func normalizePrefix(value string) string {
	cleaned := normalizePath(value)
	if !strings.HasSuffix(cleaned, "/") {
		cleaned += "/"
	}
	return cleaned
}

func modeAllowed(actual string, maximum string) bool {
	actualValue, errA := strconv.ParseInt(actual, 8, 64)
	maxValue, errB := strconv.ParseInt(maximum, 8, 64)
	if errA != nil || errB != nil {
		return false
	}
	return actualValue&^maxValue == 0
}

func wholeDays(start time.Time, end time.Time) int {
	if end.Before(start) {
		return 0
	}
	return int(end.Sub(start).Hours() / 24)
}

func formatTime(t time.Time) string {
	return t.UTC().Format(time.RFC3339)
}

func sortWarnings(warnings []warningRow) {
	sort.Slice(warnings, func(i, j int) bool {
		if warnings[i].Code != warnings[j].Code {
			return warnings[i].Code < warnings[j].Code
		}
		if warnings[i].SubjectPath != warnings[j].SubjectPath {
			return warnings[i].SubjectPath < warnings[j].SubjectPath
		}
		if warnings[i].SourcePath != warnings[j].SourcePath {
			return warnings[i].SourcePath < warnings[j].SourcePath
		}
		if warnings[i].SourceLine != warnings[j].SourceLine {
			return warnings[i].SourceLine < warnings[j].SourceLine
		}
		return warnings[i].Detail < warnings[j].Detail
	})
}

func prepareOutDir(outDir string) error {
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return err
	}
	entries, err := os.ReadDir(outDir)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		if strings.HasSuffix(entry.Name(), ".json") {
			if err := os.Remove(filepath.Join(outDir, entry.Name())); err != nil {
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
