package main

import (
	"bytes"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"fmt"
	"io"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"github.com/pelletier/go-toml/v2"
	"gopkg.in/yaml.v3"
	_ "modernc.org/sqlite"
)

const (
	dossierDoc = "dossier"
)

var (
	ruleOrder = []string{"AR-001", "RM-002", "TR-003", "RT-004", "LG-005"}
	topTOMLKeys = []string{"workspace", "artifacts", "owners", "policy_pack", "models"}
)

type exceptionRow struct {
	ExceptionID   string
	RuleID        string
	ScopeClass    string
	ScopeID       string
	TargetPath    string
	GrantValue    string
	ModelAllowlist string
	AmendmentSeq  int
	Active        bool
	ValidFromRun  string
	ValidUntilRun string
	Predicate     string
	SourceDoc     string
	SourceOrdinal int
	Enabled       bool
	DocOrder      int
}

type credMapRow struct {
	URIPrefix  string
	Username   string
	CredRef    string
	MatchMode  string
	SourceDoc  string
	RowIndex   int
}

type retentionEntry struct {
	Class string
	Rank  int
}

type policyPackRef struct {
	Name    string
	Path    string
	Enabled bool
}

type profileInfo struct {
	RelDir           string
	WorkspaceID      string
	RunID            string
	DefaultRetention string
	Files            map[string][]byte
	PackRefs         []policyPackRef
	PackOrder        []string
}

type experimentInfo struct {
	ID           string
	Stage        string
	PublicRead   *bool
	Stores       []storeInfo
	RetentionClass string
	RetentionOverride bool
	Quarantine   bool
	Raw          map[string]any
}

type storeInfo struct {
	Name       string
	PublicRead bool
}

type modelInfo struct {
	Name         string
	Stage        string
	ExperimentID string
	AliasMutable *bool
	Quarantine   bool
	PromotionLocked bool
	Raw          map[string]any
}

type trackingExpInfo struct {
	ID              string
	RetentionClass  string
	RetentionOverride bool
	HasClass        bool
	Raw             map[string]any
}

type trackingInfo struct {
	URI     string
	HasURI  bool
	Servers map[string]string
	Experiments []trackingExpInfo
	Raw     map[string]any
}

type policyAction struct {
	SourceFile  string
	ProfileID   string
	RuleID      string
	TargetPath  string
	OldValue    string
	NewValue    string
	ExceptionID string
	Status      string
	ReasonCode  string
}

type exceptionResolution struct {
	ProfileID        string
	SourceDoc        string
	SourceOrdinal    int
	ExceptionID      string
	RuleID           string
	TargetPath       string
	ScopeClass       string
	ScopeID          string
	AmendmentSeq     int
	ResolutionStatus string
	ReasonCode       string
	PrecedenceKey    string
}

type uriRedaction struct {
	SourceFile string
	ProfileID  string
	TargetPath string
	Username   string
	URIPrefix  string
	CredRef    string
	Status     string
}

type lineageEdge struct {
	ProfileID             string
	ModelName             string
	ExperimentID          string
	ExperimentPresent     bool
	ExperimentQuarantined bool
	ModelQuarantinedAfter bool
}

type profileContext struct {
	info        profileInfo
	exceptions  []exceptionRow
	creds       []credMapRow
	retention   map[string]int
	experiments map[string]*experimentInfo
	models      []modelInfo
	tracking    *trackingInfo
	workspace   map[string]any
	registry    map[string]any
	expYAML     map[string]any
	trackYAML   map[string]any
}

func run(dossierPath, configDir, outDir, evidencePath string) error {
	dossierBytes, err := os.ReadFile(dossierPath)
	if err != nil {
		return fmt.Errorf("read dossier: %w", err)
	}
	dossierText := string(dossierBytes)
	dossierPolicy, err := parsePolicyDocument(dossierText, dossierDoc, true)
	if err != nil {
		return err
	}
	if len(parseTableByHeader(dossierText, exceptionHeader())) == 0 {
		return fmt.Errorf("required table Active Policy Exceptions missing from dossier")
	}
	if len(parseTableByHeader(dossierText, credHeader())) == 0 {
		return fmt.Errorf("required table Credential Reference Map missing from dossier")
	}
	if len(parseTableByHeader(dossierText, retentionHeader())) == 0 {
		return fmt.Errorf("required table Retention Class Lattice missing from dossier")
	}

	profiles, allInputPaths, err := discoverProfiles(configDir)
	if err != nil {
		return err
	}
	if len(profiles) == 0 {
		return fmt.Errorf("no profile with workspace.toml found under %s", configDir)
	}
	sort.Slice(profiles, func(i, j int) bool {
		return profiles[i].RelDir < profiles[j].RelDir
	})

	if err := cleanOutputDir(outDir); err != nil {
		return err
	}
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return err
	}

	var (
		allActions     []policyAction
		allResolutions []exceptionResolution
		allRedactions  []uriRedaction
		allLineage     []lineageEdge
		outputPaths    []string
	)

	for _, prof := range profiles {
		ctx, err := buildProfileContext(prof, dossierPolicy, configDir)
		if err != nil {
			return err
		}
		acts, res, red, lin, err := replayProfile(ctx)
		if err != nil {
			return err
		}
		allActions = append(allActions, acts...)
		allResolutions = append(allResolutions, res...)
		allRedactions = append(allRedactions, red...)
		allLineage = append(allLineage, lin...)

		for rel, content := range ctx.info.Files {
			outPath := filepath.Join(outDir, filepath.FromSlash(rel))
			if err := os.MkdirAll(filepath.Dir(outPath), 0o755); err != nil {
				return err
			}
			if err := os.WriteFile(outPath, content, 0o644); err != nil {
				return err
			}
			outputPaths = append(outputPaths, rel)
		}
	}

	sort.Strings(allInputPaths)
	sort.Strings(outputPaths)

	inputDigest, err := configsDigest(configDir, allInputPaths)
	if err != nil {
		return err
	}
	outputDigest, err := configsDigest(outDir, outputPaths)
	if err != nil {
		return err
	}
	return writeEvidence(evidencePath, dossierBytes, inputDigest, outputDigest, len(profiles), allActions, allResolutions, allRedactions, allLineage)
}

func exceptionHeader() string {
	return "exception_id | rule_id | scope_class | scope_id | target_path | grant_value | model_allowlist | amendment_seq | active | valid_from_run | valid_until_run | predicate"
}

func credHeader() string {
	return "uri_prefix | username | cred_ref | match_mode"
}

func retentionHeader() string {
	return "class | rank"
}

func cleanOutputDir(outDir string) error {
	info, err := os.Stat(outDir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	if !info.IsDir() {
		return fmt.Errorf("%s is not a directory", outDir)
	}
	return filepath.Walk(outDir, func(path string, fi os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if path == outDir {
			return nil
		}
		if fi.IsDir() {
			return os.RemoveAll(path)
		}
		return os.Remove(path)
	})
}

func discoverProfiles(configDir string) ([]profileInfo, []string, error) {
	var profiles []profileInfo
	allPaths := map[string]struct{}{}

	addProfile := func(relDir string) error {
		profDir := configDir
		if relDir != "" {
			profDir = filepath.Join(configDir, filepath.FromSlash(relDir))
		}
		wsPath := filepath.Join(profDir, "workspace.toml")
		wsBytes, err := os.ReadFile(wsPath)
		if err != nil {
			return fmt.Errorf("read workspace.toml for profile %q: %w", relDir, err)
		}
		ws, packRefs, packOrder, err := parseWorkspace(wsBytes)
		if err != nil {
			return fmt.Errorf("parse workspace.toml for profile %q: %w", relDir, err)
		}
		files := map[string][]byte{}
		collect := func(baseRel, abs string) error {
			entries, err := os.ReadDir(abs)
			if err != nil {
				return err
			}
			for _, e := range entries {
				if e.IsDir() {
					continue
				}
				name := e.Name()
				ext := strings.ToLower(filepath.Ext(name))
				if ext != ".yaml" && ext != ".yml" && ext != ".toml" {
					continue
				}
				rel := name
				if baseRel != "" {
					rel = baseRel + "/" + name
				}
				if err := validateRelPath(rel); err != nil {
					return err
				}
				b, err := os.ReadFile(filepath.Join(abs, name))
				if err != nil {
					return err
				}
				files[rel] = b
				allPaths[rel] = struct{}{}
			}
			return nil
		}
		if err := collect(relDir, profDir); err != nil {
			return err
		}
		for _, pack := range packRefs {
			packRel := pack.Path
			if relDir != "" {
				packRel = relDir + "/" + strings.ReplaceAll(pack.Path, "\\", "/")
			}
			packRel = strings.ReplaceAll(packRel, "\\", "/")
			if err := validateRelPath(packRel); err != nil {
				return err
			}
		}
		profiles = append(profiles, profileInfo{
			RelDir:      relDir,
			WorkspaceID: getString(ws, "workspace", "id"),
			RunID:       getStringDefault(ws, "default-run", "workspace", "governance", "run_id"),
			DefaultRetention: getStringDefault(ws, "standard-90d", "workspace", "retention", "default_class"),
			Files:       files,
			PackRefs:    packRefs,
			PackOrder:   packOrder,
		})
		return nil
	}

	rootWS := filepath.Join(configDir, "workspace.toml")
	if _, err := os.Stat(rootWS); err == nil {
		if err := addProfile(""); err != nil {
			return nil, nil, err
		}
	}
	entries, err := os.ReadDir(configDir)
	if err != nil {
		return nil, nil, err
	}
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		subRel := e.Name()
		subWS := filepath.Join(configDir, subRel, "workspace.toml")
		if _, err := os.Stat(subWS); err == nil {
			if err := addProfile(subRel); err != nil {
				return nil, nil, err
			}
		}
	}
	// one-level subdir files under config root (non-profile dirs)
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		subRel := e.Name()
		subWS := filepath.Join(configDir, subRel, "workspace.toml")
		if _, err := os.Stat(subWS); err == nil {
			continue
		}
		subDir := filepath.Join(configDir, subRel)
		subEntries, err := os.ReadDir(subDir)
		if err != nil {
			return nil, nil, err
		}
		for _, se := range subEntries {
			if se.IsDir() {
				continue
			}
			ext := strings.ToLower(filepath.Ext(se.Name()))
			if ext != ".yaml" && ext != ".yml" && ext != ".toml" {
				continue
			}
			rel := subRel + "/" + se.Name()
			if err := validateRelPath(rel); err != nil {
				return nil, nil, err
			}
		}
	}

	pathList := make([]string, 0, len(allPaths))
	for p := range allPaths {
		pathList = append(pathList, p)
	}
	sort.Strings(pathList)
	return profiles, pathList, nil
}

func validateRelPath(rel string) error {
	if strings.Contains(rel, "\x00") {
		return fmt.Errorf("invalid path %q: contains NUL", rel)
	}
	if strings.Contains(rel, `\`) {
		return fmt.Errorf("invalid path %q: contains backslash", rel)
	}
	if filepath.IsAbs(rel) {
		return fmt.Errorf("invalid path %q: absolute", rel)
	}
	parts := strings.Split(rel, "/")
	for _, p := range parts {
		if p == ".." {
			return fmt.Errorf("invalid path %q: contains ..", rel)
		}
	}
	return nil
}

type parsedPolicy struct {
	exceptions []exceptionRow
	creds      []credMapRow
	retention  map[string]int
}

func parsePolicyDocument(text, sourceDoc string, enabled bool) (parsedPolicy, error) {
	pp := parsedPolicy{retention: map[string]int{}}
	ordinal := 0
	for _, cols := range parseTableByHeader(text, exceptionHeader()) {
		ordinal++
		seq, _ := strconv.Atoi(strings.TrimSpace(cols[7]))
		pp.exceptions = append(pp.exceptions, exceptionRow{
			ExceptionID:    cols[0],
			RuleID:         cols[1],
			ScopeClass:     cols[2],
			ScopeID:        cols[3],
			TargetPath:     cols[4],
			GrantValue:     cols[5],
			ModelAllowlist: cols[6],
			AmendmentSeq:   seq,
			Active:         strings.EqualFold(cols[8], "yes"),
			ValidFromRun:   cols[9],
			ValidUntilRun:  cols[10],
			Predicate:      cols[11],
			SourceDoc:      sourceDoc,
			SourceOrdinal:  ordinal,
			Enabled:        enabled,
		})
	}
	rowIdx := 0
	for _, cols := range parseTableByHeader(text, credHeader()) {
		matchMode := "longest_prefix"
		if len(cols) >= 4 && strings.TrimSpace(cols[3]) != "" {
			matchMode = cols[3]
		}
		pp.creds = append(pp.creds, credMapRow{
			URIPrefix: cols[0],
			Username:  cols[1],
			CredRef:   cols[2],
			MatchMode: matchMode,
			SourceDoc: sourceDoc,
			RowIndex:  rowIdx,
		})
		rowIdx++
	}
	for _, cols := range parseTableByHeader(text, retentionHeader()) {
		rank, err := strconv.Atoi(strings.TrimSpace(cols[1]))
		if err != nil {
			return pp, fmt.Errorf("invalid retention rank for class %q", cols[0])
		}
		pp.retention[cols[0]] = rank
	}
	return pp, nil
}

func parseTableByHeader(text, header string) [][]string {
	var rows [][]string
	lines := strings.Split(text, "\n")
	inFence := false
	inTable := false
	expectedCols := len(splitHeader(header))
	for _, line := range lines {
		trim := strings.TrimSpace(line)
		if strings.HasPrefix(trim, "```") {
			inFence = !inFence
			continue
		}
		if inFence {
			continue
		}
		if !inTable {
			if isHeaderRow(trim, header) {
				inTable = true
			}
			continue
		}
		if !strings.HasPrefix(trim, "|") {
			break
		}
		if strings.Contains(trim, "---") {
			continue
		}
		cols := splitTableRow(trim)
		if len(cols) == 0 {
			continue
		}
		if len(cols) < expectedCols {
			for len(cols) < expectedCols {
				cols = append(cols, "")
			}
		}
		rows = append(rows, cols[:expectedCols])
	}
	return rows
}

func isHeaderRow(line, header string) bool {
	return normalizeHeader(line) == normalizeHeader(header)
}

func normalizeHeader(s string) string {
	parts := splitTableRow(strings.TrimSpace(s))
	for i := range parts {
		parts[i] = strings.TrimSpace(parts[i])
	}
	return strings.Join(parts, "|")
}

func splitHeader(header string) []string {
	return strings.Split(header, "|")
}

func splitTableRow(line string) []string {
	line = strings.TrimSpace(line)
	if strings.HasPrefix(line, "|") {
		line = line[1:]
	}
	if strings.HasSuffix(line, "|") {
		line = line[:len(line)-1]
	}
	var cols []string
	var cur strings.Builder
	for i := 0; i < len(line); i++ {
		if line[i] == '\\' && i+1 < len(line) && line[i+1] == '|' {
			cur.WriteByte('|')
			i++
			continue
		}
		if line[i] == '|' {
			cols = append(cols, trimCell(cur.String()))
			cur.Reset()
			continue
		}
		cur.WriteByte(line[i])
	}
	cols = append(cols, trimCell(cur.String()))
	return cols
}

func trimCell(s string) string {
	if len(s) >= 2 && s[0] == ' ' && s[len(s)-1] == ' ' {
		return s[1 : len(s)-1]
	}
	if strings.HasPrefix(s, " ") {
		s = s[1:]
	}
	if strings.HasSuffix(s, " ") {
		s = s[:len(s)-1]
	}
	return s
}

func parseWorkspace(data []byte) (map[string]any, []policyPackRef, []string, error) {
	var root map[string]any
	if err := toml.Unmarshal(data, &root); err != nil {
		return nil, nil, nil, err
	}
	var packs []policyPackRef
	if raw, ok := root["policy_pack"]; ok {
		for _, item := range raw.([]any) {
			m := item.(map[string]any)
			enabled := true
			if v, ok := m["enabled"]; ok {
				enabled = toBool(v)
			}
			packs = append(packs, policyPackRef{
				Name:    fmt.Sprintf("%v", m["name"]),
				Path:    strings.ReplaceAll(fmt.Sprintf("%v", m["path"]), "\\", "/"),
				Enabled: enabled,
			})
		}
	}
	packOrder := getStringSlice(root, "workspace", "governance", "policy_pack_order")
	if len(packOrder) == 0 {
		for _, p := range packs {
			packOrder = append(packOrder, p.Name)
		}
	}
	return root, packs, packOrder, nil
}

func getString(m map[string]any, keys ...string) string {
	v := navigate(m, keys...)
	if v == nil {
		return ""
	}
	return fmt.Sprintf("%v", v)
}

func getStringDefault(m map[string]any, def string, keys ...string) string {
	v := getString(m, keys...)
	if v == "" {
		return def
	}
	return v
}

func getStringSlice(m map[string]any, keys ...string) []string {
	v := navigate(m, keys...)
	if v == nil {
		return nil
	}
	arr, ok := v.([]any)
	if !ok {
		return nil
	}
	out := make([]string, 0, len(arr))
	for _, item := range arr {
		out = append(out, fmt.Sprintf("%v", item))
	}
	return out
}

func navigate(m map[string]any, keys ...string) any {
	if len(keys) == 0 {
		return m
	}
	cur := any(m)
	for i, k := range keys {
		mp, ok := cur.(map[string]any)
		if !ok {
			return nil
		}
		if v, ok := mp[k]; ok {
			cur = v
			continue
		}
		dotted := strings.Join(keys[i:], ".")
		if v, ok := mp[dotted]; ok {
			return v
		}
		return nil
	}
	return cur
}

func toBool(v any) bool {
	switch t := v.(type) {
	case bool:
		return t
	case string:
		return strings.EqualFold(t, "true")
	default:
		return fmt.Sprintf("%v", t) == "true"
	}
}

func boolStr(v bool) string {
	if v {
		return "true"
	}
	return "false"
}

func boolStrPtr(p *bool) string {
	if p == nil {
		return "false"
	}
	return boolStr(*p)
}

func escapeTargetID(id string) string {
	var b strings.Builder
	for _, r := range id {
		switch r {
		case '\\', ']', '|':
			b.WriteByte('\\')
		}
		b.WriteRune(r)
	}
	return b.String()
}

func scopeRank(class string) int {
	switch class {
	case "experiment":
		return 4
	case "model":
		return 3
	case "workspace":
		return 2
	case "global":
		return 1
	default:
		return 0
	}
}

func inRunWindow(runID, from, until string) bool {
	if from != "" && runID < from {
		return false
	}
	if until != "" && runID >= until {
		return false
	}
	return true
}

func precedenceKey(ruleID, targetPath string) string {
	return ruleID + "\x1f" + targetPath
}

func valueDigest(ruleID, targetPath, oldVal, newVal, status string) string {
	h := sha256.New()
	io.WriteString(h, ruleID)
	io.WriteString(h, "\x1f")
	io.WriteString(h, targetPath)
	io.WriteString(h, "\x1f")
	io.WriteString(h, oldVal)
	io.WriteString(h, "\x1f")
	io.WriteString(h, newVal)
	io.WriteString(h, "\x1f")
	io.WriteString(h, status)
	io.WriteString(h, "\n")
	return hex.EncodeToString(h.Sum(nil))
}

func configsDigest(dir string, relPaths []string) (string, error) {
	h := sha256.New()
	for _, rel := range relPaths {
		b, err := os.ReadFile(filepath.Join(dir, filepath.FromSlash(rel)))
		if err != nil {
			return "", err
		}
		io.WriteString(h, rel)
		io.WriteString(h, "\n")
		h.Write(b)
		io.WriteString(h, "\n")
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

func buildProfileContext(prof profileInfo, dossierPolicy parsedPolicy, configDir string) (*profileContext, error) {
	ctx := &profileContext{
		info:        prof,
		retention:   map[string]int{},
		experiments: map[string]*experimentInfo{},
	}
	for k, v := range dossierPolicy.retention {
		ctx.retention[k] = v
	}

	var mergedEx []exceptionRow
	for _, ex := range dossierPolicy.exceptions {
		ex.DocOrder = 0
		mergedEx = append(mergedEx, ex)
	}
	var mergedCreds []credMapRow
	mergedCreds = append(mergedCreds, dossierPolicy.creds...)

	packByName := map[string]policyPackRef{}
	for _, p := range prof.PackRefs {
		packByName[p.Name] = p
	}
	profDir := configDir
	if prof.RelDir != "" {
		profDir = filepath.Join(configDir, filepath.FromSlash(prof.RelDir))
	}
	docOrder := 1
	for _, name := range prof.PackOrder {
		ref, ok := packByName[name]
		if !ok {
			continue
		}
		packPath := filepath.Join(profDir, filepath.FromSlash(ref.Path))
		packBytes, err := os.ReadFile(packPath)
		if err != nil {
			return nil, fmt.Errorf("read policy pack %q: %w", ref.Path, err)
		}
		packDoc := ref.Path
		if prof.RelDir != "" {
			packDoc = prof.RelDir + "/" + ref.Path
		}
		pp, err := parsePolicyDocument(string(packBytes), packDoc, ref.Enabled)
		if err != nil {
			return nil, err
		}
		for i := range pp.exceptions {
			pp.exceptions[i].SourceDoc = packDoc
			pp.exceptions[i].Enabled = ref.Enabled
			pp.exceptions[i].DocOrder = docOrder
		}
		docOrder++
		if ref.Enabled {
			mergedEx = append(mergedEx, pp.exceptions...)
		}
		for _, c := range pp.creds {
			c.SourceDoc = packDoc
			c.RowIndex += len(mergedCreds)
			mergedCreds = append(mergedCreds, c)
		}
		for k, v := range pp.retention {
			ctx.retention[k] = v
		}
	}
	ctx.exceptions = mergedEx
	ctx.creds = mergedCreds

	for rel, raw := range prof.Files {
		base := filepath.Base(rel)
		switch base {
		case "workspace.toml":
			var root map[string]any
			if err := toml.Unmarshal(raw, &root); err != nil {
				return nil, fmt.Errorf("parse %s: %w", rel, err)
			}
			ctx.workspace = root
		case "experiments.yaml", "experiments.yml":
			var root map[string]any
			if err := yaml.Unmarshal(raw, &root); err != nil {
				return nil, fmt.Errorf("parse %s: %w", rel, err)
			}
			ctx.expYAML = root
			if arr, ok := root["experiments"].([]any); ok {
				for _, item := range arr {
					m := item.(map[string]any)
					ei := parseExperiment(m)
					ctx.experiments[ei.ID] = ei
				}
			}
		case "registry.toml":
			var root map[string]any
			if err := toml.Unmarshal(raw, &root); err != nil {
				return nil, fmt.Errorf("parse %s: %w", rel, err)
			}
			ctx.registry = root
			if arr, ok := root["models"].([]any); ok {
				for _, item := range arr {
					ctx.models = append(ctx.models, parseModel(item.(map[string]any)))
				}
			}
		case "tracking.yaml", "tracking.yml":
			var root map[string]any
			if err := yaml.Unmarshal(raw, &root); err != nil {
				return nil, fmt.Errorf("parse %s: %w", rel, err)
			}
			ctx.trackYAML = root
			ctx.tracking = parseTracking(root)
		}
	}
	return ctx, nil
}

func parseExperiment(m map[string]any) *experimentInfo {
	ei := &experimentInfo{Raw: m, ID: fmt.Sprintf("%v", m["id"])}
	if v, ok := m["stage"]; ok {
		ei.Stage = fmt.Sprintf("%v", v)
	}
	if art, ok := m["artifacts"].(map[string]any); ok {
		if pr, ok := art["public_read"]; ok {
			b := toBool(pr)
			ei.PublicRead = &b
		}
		if stores, ok := art["stores"].([]any); ok {
			for _, s := range stores {
				sm := s.(map[string]any)
				ei.Stores = append(ei.Stores, storeInfo{
					Name:       fmt.Sprintf("%v", sm["name"]),
					PublicRead: toBool(sm["public_read"]),
				})
			}
		}
	}
	if ret, ok := m["retention"].(map[string]any); ok {
		ei.RetentionOverride = toBool(ret["override"])
		if cls, ok := ret["class"]; ok {
			ei.RetentionClass = fmt.Sprintf("%v", cls)
		}
	}
	if gov, ok := m["governance"].(map[string]any); ok {
		ei.Quarantine = toBool(gov["quarantine"])
	}
	return ei
}

func parseModel(m map[string]any) modelInfo {
	mi := modelInfo{Raw: m, Name: fmt.Sprintf("%v", m["name"])}
	if v, ok := m["stage"]; ok {
		mi.Stage = fmt.Sprintf("%v", v)
	}
	if v, ok := m["experiment_id"]; ok {
		mi.ExperimentID = fmt.Sprintf("%v", v)
	}
	if aliases, ok := m["aliases"].(map[string]any); ok {
		if mv, ok := aliases["mutable"]; ok {
			b := toBool(mv)
			mi.AliasMutable = &b
		}
	}
	if v, ok := m["aliases.mutable"]; ok {
		b := toBool(v)
		mi.AliasMutable = &b
	}
	if gov, ok := m["governance"].(map[string]any); ok {
		mi.Quarantine = toBool(gov["quarantine"])
	} else if v, ok := m["governance.quarantine"]; ok {
		mi.Quarantine = toBool(v)
	}
	if prom, ok := m["promotion"].(map[string]any); ok {
		mi.PromotionLocked = toBool(prom["locked"])
	} else if v, ok := m["promotion.locked"]; ok {
		mi.PromotionLocked = toBool(v)
	}
	return mi
}

func parseTracking(root map[string]any) *trackingInfo {
	ti := &trackingInfo{Raw: root["tracking"].(map[string]any), Servers: map[string]string{}}
	tr := ti.Raw
	if uri, ok := tr["uri"]; ok {
		ti.URI = fmt.Sprintf("%v", uri)
		ti.HasURI = true
	}
	if servers, ok := tr["servers"].([]any); ok {
		for _, s := range servers {
			sm := s.(map[string]any)
			ti.Servers[fmt.Sprintf("%v", sm["name"])] = fmt.Sprintf("%v", sm["uri"])
		}
	}
	if exps, ok := tr["experiments"].([]any); ok {
		for _, e := range exps {
			em := e.(map[string]any)
			te := trackingExpInfo{ID: fmt.Sprintf("%v", em["id"]), Raw: em}
			if ret, ok := em["retention"].(map[string]any); ok {
				te.RetentionOverride = toBool(ret["override"])
				if cls, ok := ret["class"]; ok {
					te.RetentionClass = fmt.Sprintf("%v", cls)
					te.HasClass = true
				}
			}
			ti.Experiments = append(ti.Experiments, te)
		}
	}
	return ti
}

func replayProfile(ctx *profileContext) ([]policyAction, []exceptionResolution, []uriRedaction, []lineageEdge, error) {
	var fileRels []string
	for rel := range ctx.info.Files {
		fileRels = append(fileRels, rel)
	}
	sort.Strings(fileRels)

	var actions []policyAction
	var resolutions []exceptionResolution
	var redactions []uriRedaction
	var lineage []lineageEdge

	for _, rel := range fileRels {
		base := filepath.Base(rel)
		for _, rule := range ruleOrder {
			var (
				acts []policyAction
				res  []exceptionResolution
				red  []uriRedaction
				lin  []lineageEdge
				err  error
			)
			switch rule {
			case "AR-001":
				if base == "workspace.toml" || base == "experiments.yaml" || base == "experiments.yml" {
					acts, res, err = applyAR001(ctx, rel)
				}
			case "RM-002":
				if base == "registry.toml" {
					acts, res, err = applyRM002(ctx, rel)
				}
			case "TR-003":
				if base == "tracking.yaml" || base == "tracking.yml" {
					acts, res, red, err = applyTR003(ctx, rel)
				}
			case "RT-004":
				if base == "tracking.yaml" || base == "tracking.yml" {
					acts, res, err = applyRT004(ctx, rel)
				}
			case "LG-005":
				if base == "registry.toml" {
					acts, res, lin, err = applyLG005(ctx, rel)
				}
			}
			if err != nil {
				return nil, nil, nil, nil, err
			}
			actions = append(actions, acts...)
			resolutions = append(resolutions, res...)
			redactions = append(redactions, red...)
			lineage = append(lineage, lin...)
		}
	}
	return actions, resolutions, redactions, lineage, nil
}

type targetScope struct {
	ExperimentID string
	ModelName    string
	Workspace    bool
}

func targetScopeFor(path string) targetScope {
	var ts targetScope
	if path == "workspace.artifacts.public_read" {
		ts.Workspace = true
		return ts
	}
	if strings.HasPrefix(path, "experiments[id=") {
		id, _ := parseBracketID(path, "experiments[id=", "].")
		ts.ExperimentID = id
	}
	if strings.HasPrefix(path, "models[name=") {
		name, _ := parseBracketID(path, "models[name=", "].")
		ts.ModelName = name
	}
	return ts
}

func parseBracketID(path, prefix, suffix string) (string, bool) {
	if !strings.HasPrefix(path, prefix) {
		return "", false
	}
	rest := path[len(prefix):]
	end := strings.Index(rest, suffix)
	if end < 0 {
		return "", false
	}
	return unescapeTargetID(rest[:end]), true
}

func unescapeTargetID(s string) string {
	var b strings.Builder
	for i := 0; i < len(s); i++ {
		if s[i] == '\\' && i+1 < len(s) {
			b.WriteByte(s[i+1])
			i++
			continue
		}
		b.WriteByte(s[i])
	}
	return b.String()
}

func scopeMatches(ex exceptionRow, ts targetScope, workspaceID string) bool {
	switch ex.ScopeClass {
	case "global":
		return ex.ScopeID == "*"
	case "workspace":
		return ex.ScopeID == workspaceID
	case "experiment":
		return ts.ExperimentID != "" && ex.ScopeID == ts.ExperimentID
	case "model":
		return ts.ModelName != "" && ex.ScopeID == ts.ModelName
	default:
		return false
	}
}

func matchingExceptions(ctx *profileContext, ruleID, targetPath string) []exceptionRow {
	var out []exceptionRow
	for _, ex := range ctx.exceptions {
		if !ex.Enabled || ex.RuleID != ruleID || ex.TargetPath != targetPath {
			continue
		}
		out = append(out, ex)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].DocOrder != out[j].DocOrder {
			return out[i].DocOrder < out[j].DocOrder
		}
		return out[i].SourceOrdinal < out[j].SourceOrdinal
	})
	return out
}

func resolveExceptions(ctx *profileContext, ruleID, targetPath string, ts targetScope) ([]exceptionRow, []exceptionResolution) {
	runID := ctx.info.RunID
	wsID := ctx.info.WorkspaceID
	rows := matchingExceptions(ctx, ruleID, targetPath)

	var active []exceptionRow
	for _, ex := range rows {
		if ex.Active && inRunWindow(runID, ex.ValidFromRun, ex.ValidUntilRun) && scopeMatches(ex, ts, wsID) {
			active = append(active, ex)
		}
	}

	var winner exceptionRow
	if len(active) > 0 {
		sort.Slice(active, func(i, j int) bool {
			a, b := active[i], active[j]
			if scopeRank(a.ScopeClass) != scopeRank(b.ScopeClass) {
				return scopeRank(a.ScopeClass) > scopeRank(b.ScopeClass)
			}
			if a.AmendmentSeq != b.AmendmentSeq {
				return a.AmendmentSeq > b.AmendmentSeq
			}
			if a.DocOrder != b.DocOrder {
				return a.DocOrder > b.DocOrder
			}
			return a.SourceOrdinal > b.SourceOrdinal
		})
		winner = active[0]
	}

	sameEx := func(a, b exceptionRow) bool {
		return a.ExceptionID == b.ExceptionID && a.SourceOrdinal == b.SourceOrdinal && a.SourceDoc == b.SourceDoc
	}

	var resolutions []exceptionResolution
	for _, ex := range rows {
		rec := exceptionResolution{
			ProfileID: wsID, SourceDoc: ex.SourceDoc, SourceOrdinal: ex.SourceOrdinal,
			ExceptionID: ex.ExceptionID, RuleID: ruleID, TargetPath: targetPath,
			ScopeClass: ex.ScopeClass, ScopeID: ex.ScopeID, AmendmentSeq: ex.AmendmentSeq,
			PrecedenceKey: precedenceKey(ruleID, targetPath),
		}
		switch {
		case !ex.Active:
			rec.ResolutionStatus = "inactive"
			rec.ReasonCode = "inactive"
		case !inRunWindow(runID, ex.ValidFromRun, ex.ValidUntilRun):
			rec.ResolutionStatus = "window_miss"
			rec.ReasonCode = "window_miss"
		case !scopeMatches(ex, ts, wsID):
			rec.ResolutionStatus = "scope_miss"
			rec.ReasonCode = "scope_miss"
		case len(active) > 0 && sameEx(ex, winner):
			rec.ResolutionStatus = "winner"
			rec.ReasonCode = "winning_exception"
		default:
			rec.ResolutionStatus = "skipped_conflict"
			rec.ReasonCode = "lower_precedence_exception"
		}
		resolutions = append(resolutions, rec)
	}

	if len(active) == 0 {
		return nil, resolutions
	}
	return active, resolutions
}

func inAllowlist(allowlist, name string) bool {
	if strings.TrimSpace(allowlist) == "" {
		return false
	}
	for _, part := range strings.Split(allowlist, ",") {
		if strings.TrimSpace(part) == name {
			return true
		}
	}
	return false
}

func rm002PredicateFail(ex exceptionRow, model modelInfo, ctx *profileContext) (bool, string) {
	if model.Stage != "staging" {
		return true, "stage"
	}
	if !inAllowlist(ex.ModelAllowlist, model.Name) {
		return true, "allowlist"
	}
	if model.ExperimentID == "" {
		return true, "experiment_missing"
	}
	exp, ok := ctx.experiments[model.ExperimentID]
	if !ok {
		return true, "experiment_missing"
	}
	if exp.Quarantine {
		return true, "experiment_quarantined"
	}
	if model.Quarantine {
		return true, "model_quarantined"
	}
	if model.PromotionLocked {
		return true, "promotion_locked"
	}
	if ex.Predicate != "" && ex.Predicate != "stage=staging" {
		return true, "predicate"
	}
	return false, ""
}

func makeAction(sourceFile, profileID, ruleID, target, oldVal, newVal, exID, status, reason string) policyAction {
	return policyAction{
		SourceFile: sourceFile, ProfileID: profileID, RuleID: ruleID, TargetPath: target,
		OldValue: oldVal, NewValue: newVal, ExceptionID: exID, Status: status, ReasonCode: reason,
	}
}

func skippedConflictActions(sourceFile, profileID, ruleID, target, oldVal string, candidates []exceptionRow) []policyAction {
	if len(candidates) <= 1 {
		return nil
	}
	losers := candidates[1:]
	sort.Slice(losers, func(i, j int) bool {
		a, b := losers[i], losers[j]
		if scopeRank(a.ScopeClass) != scopeRank(b.ScopeClass) {
			return scopeRank(a.ScopeClass) > scopeRank(b.ScopeClass)
		}
		if a.AmendmentSeq != b.AmendmentSeq {
			return a.AmendmentSeq > b.AmendmentSeq
		}
		if a.DocOrder != b.DocOrder {
			return a.DocOrder > b.DocOrder
		}
		return a.SourceOrdinal > b.SourceOrdinal
	})
	var acts []policyAction
	for _, l := range losers {
		acts = append(acts, makeAction(sourceFile, profileID, ruleID, target, oldVal, l.GrantValue, l.ExceptionID, "skipped_conflict", "lower_precedence_exception"))
	}
	return acts
}

func applyAR001(ctx *profileContext, rel string) ([]policyAction, []exceptionResolution, error) {
	base := filepath.Base(rel)
	profileID := ctx.info.WorkspaceID
	var actions []policyAction
	var allRes []exceptionResolution

	type arTarget struct {
		path   string
		oldVal string
		setVal func(bool)
		ts     targetScope
	}
	var targets []arTarget

	if base == "workspace.toml" {
		art := navigateMap(ctx.workspace, "artifacts")
		old := "false"
		if art != nil {
			if pr, ok := art["public_read"]; ok {
				old = boolStr(toBool(pr))
			}
		}
		targets = append(targets, arTarget{
			path: "workspace.artifacts.public_read", oldVal: old, ts: targetScope{Workspace: true},
			setVal: func(v bool) {
				if art == nil {
					art = map[string]any{}
					ctx.workspace["artifacts"] = art
				}
				art["public_read"] = v
			},
		})
	} else {
		for _, exp := range sortedExperiments(ctx) {
			id := exp.ID
			tp := fmt.Sprintf("experiments[id=%s].artifacts.public_read", escapeTargetID(id))
			old := boolStrPtr(exp.PublicRead)
			e := exp
			targets = append(targets, arTarget{
				path: tp, oldVal: old, ts: targetScope{ExperimentID: id},
				setVal: func(v bool) {
					art := ensureMap(e.Raw, "artifacts")
					art["public_read"] = v
					b := v
					e.PublicRead = &b
				},
			})
			for _, st := range exp.Stores {
				stp := fmt.Sprintf("experiments[id=%s].artifacts.stores[name=%s].public_read", escapeTargetID(id), escapeTargetID(st.Name))
				stOld := boolStr(st.PublicRead)
				storeName := st.Name
				targets = append(targets, arTarget{
					path: stp, oldVal: stOld, ts: targetScope{ExperimentID: id},
					setVal: func(v bool) {
						art := ensureMap(e.Raw, "artifacts")
						stores, _ := art["stores"].([]any)
						for _, si := range stores {
							sm := si.(map[string]any)
							if fmt.Sprintf("%v", sm["name"]) == storeName {
								sm["public_read"] = v
							}
						}
					},
				})
			}
		}
	}

	sort.Slice(targets, func(i, j int) bool { return targets[i].path < targets[j].path })

	for _, t := range targets {
		candidates, res := resolveExceptions(ctx, "AR-001", t.path, t.ts)
		allRes = append(allRes, res...)
		desired := "false"
		exID := ""
		reason := "base_policy"
		if len(candidates) > 0 {
			w := candidates[0]
			desired = w.GrantValue
			exID = w.ExceptionID
			reason = "winning_exception"
		}
		actions = append(actions, skippedConflictActions(rel, profileID, "AR-001", t.path, t.oldVal, candidates)...)
		status := "applied"
		if t.oldVal == desired {
			status = "already_compliant"
		} else {
			t.setVal(desired == "true")
		}
		actions = append(actions, makeAction(rel, profileID, "AR-001", t.path, t.oldVal, desired, exID, status, reason))
	}

	if base == "workspace.toml" {
		b, err := marshalDeterministicTOML(ctx.workspace)
		if err != nil {
			return nil, nil, err
		}
		ctx.info.Files[rel] = b
	} else {
		b, err := marshalYAML(ctx.expYAML)
		if err != nil {
			return nil, nil, err
		}
		ctx.info.Files[rel] = b
	}
	return actions, allRes, nil
}

func sortedExperiments(ctx *profileContext) []*experimentInfo {
	ids := make([]string, 0, len(ctx.experiments))
	for id := range ctx.experiments {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	out := make([]*experimentInfo, 0, len(ids))
	for _, id := range ids {
		out = append(out, ctx.experiments[id])
	}
	return out
}

func ensureMap(parent map[string]any, key string) map[string]any {
	if v, ok := parent[key].(map[string]any); ok {
		return v
	}
	m := map[string]any{}
	parent[key] = m
	return m
}

func navigateMap(m map[string]any, key string) map[string]any {
	if v, ok := m[key].(map[string]any); ok {
		return v
	}
	return nil
}

func applyRM002(ctx *profileContext, rel string) ([]policyAction, []exceptionResolution, error) {
	profileID := ctx.info.WorkspaceID
	var actions []policyAction
	var allRes []exceptionResolution

	type rmTarget struct {
		path string
		old  string
		model modelInfo
	}
	var targets []rmTarget
	for _, m := range ctx.models {
		tp := fmt.Sprintf("models[name=%s].aliases.mutable", escapeTargetID(m.Name))
		targets = append(targets, rmTarget{path: tp, old: boolStrPtr(m.AliasMutable), model: m})
	}
	sort.Slice(targets, func(i, j int) bool { return targets[i].path < targets[j].path })

	for _, t := range targets {
		ts := targetScope{ModelName: t.model.Name, ExperimentID: t.model.ExperimentID}
		candidates, res := resolveExceptions(ctx, "RM-002", t.path, ts)
		allRes = append(allRes, res...)

		desired := "false"
		exID := ""
		reason := "base_policy"
		if len(candidates) > 0 {
			w := candidates[0]
			if fail, failReason := rm002PredicateFail(w, t.model, ctx); fail {
				for i := range allRes {
					if allRes[i].ExceptionID == w.ExceptionID && allRes[i].SourceOrdinal == w.SourceOrdinal &&
						allRes[i].SourceDoc == w.SourceDoc && allRes[i].TargetPath == t.path &&
						allRes[i].ResolutionStatus == "winner" {
						allRes[i].ResolutionStatus = "predicate_miss"
						allRes[i].ReasonCode = failReason
					}
				}
				reason = "predicate_failed"
			} else if w.GrantValue == "true" {
				desired = "true"
				exID = w.ExceptionID
				reason = "winning_exception"
			} else {
				exID = w.ExceptionID
				desired = w.GrantValue
				reason = "winning_exception"
			}
		}
		actions = append(actions, skippedConflictActions(rel, profileID, "RM-002", t.path, t.old, candidates)...)
		status := "applied"
		if t.old == desired {
			status = "already_compliant"
		} else {
			setAliasMutable(t.model.Raw, desired == "true")
			b := desired == "true"
			t.model.AliasMutable = &b
		}
		actions = append(actions, makeAction(rel, profileID, "RM-002", t.path, t.old, desired, exID, status, reason))
	}

	b, err := marshalDeterministicTOML(ctx.registry)
	if err != nil {
		return nil, nil, err
	}
	ctx.info.Files[rel] = b
	return actions, allRes, nil
}

func setAliasMutable(m map[string]any, val bool) {
	if aliases, ok := m["aliases"].(map[string]any); ok {
		aliases["mutable"] = val
		delete(m, "aliases.mutable")
		return
	}
	if _, ok := m["aliases.mutable"]; ok {
		m["aliases.mutable"] = val
		return
	}
	m["aliases"] = map[string]any{"mutable": val}
}

func applyTR003(ctx *profileContext, rel string) ([]policyAction, []exceptionResolution, []uriRedaction, error) {
	profileID := ctx.info.WorkspaceID
	var actions []policyAction
	var redactions []uriRedaction

	type uriTarget struct {
		path string
		uri  string
		set  func(string)
	}
	var targets []uriTarget
	if ctx.tracking.HasURI {
		targets = append(targets, uriTarget{
			path: "tracking.uri", uri: ctx.tracking.URI,
			set: func(u string) { ctx.tracking.Raw["uri"] = u; ctx.tracking.URI = u },
		})
	}
	names := make([]string, 0, len(ctx.tracking.Servers))
	for n := range ctx.tracking.Servers {
		names = append(names, n)
	}
	sort.Strings(names)
	for _, n := range names {
		tp := fmt.Sprintf("tracking.servers[name=%s].uri", escapeTargetID(n))
		uri := ctx.tracking.Servers[n]
		name := n
		targets = append(targets, uriTarget{
			path: tp, uri: uri,
			set: func(u string) {
				ctx.tracking.Servers[name] = u
				if servers, ok := ctx.tracking.Raw["servers"].([]any); ok {
					for _, s := range servers {
						sm := s.(map[string]any)
						if fmt.Sprintf("%v", sm["name"]) == name {
							sm["uri"] = u
						}
					}
				}
			},
		})
	}
	sort.Slice(targets, func(i, j int) bool { return targets[i].path < targets[j].path })

	for _, t := range targets {
		newURI, red, act, err := processURI(ctx, rel, profileID, t.path, t.uri, ctx.creds)
		if err != nil {
			return nil, nil, nil, err
		}
		if act != nil {
			if act.Status == "applied" {
				t.set(newURI)
			}
			actions = append(actions, *act)
		}
		if red != nil {
			redactions = append(redactions, *red)
		}
	}

	b, err := marshalYAML(ctx.trackYAML)
	if err != nil {
		return nil, nil, nil, err
	}
	ctx.info.Files[rel] = b
	return actions, nil, redactions, nil
}

func processURI(ctx *profileContext, sourceFile, profileID, targetPath, raw string, creds []credMapRow) (string, *uriRedaction, *policyAction, error) {
	parsed, err := parseURI(raw)
	if err != nil || parsed == nil {
		act := makeAction(sourceFile, profileID, "TR-003", targetPath, raw, raw, "", "already_compliant", "uri_unmapped")
		red := &uriRedaction{SourceFile: sourceFile, ProfileID: profileID, TargetPath: targetPath, Username: "", URIPrefix: "", Status: "unsupported_scheme"}
		return raw, red, &act, nil
	}
	if parsed.unsupported {
		act := makeAction(sourceFile, profileID, "TR-003", targetPath, raw, raw, "", "already_compliant", "uri_unmapped")
		red := &uriRedaction{SourceFile: sourceFile, ProfileID: profileID, TargetPath: targetPath, Username: parsed.username, URIPrefix: "", Status: "unsupported_scheme"}
		return raw, red, &act, nil
	}
	if !parsed.hasPassword {
		act := makeAction(sourceFile, profileID, "TR-003", targetPath, raw, raw, "", "already_compliant", "uri_no_password")
		red := &uriRedaction{SourceFile: sourceFile, ProfileID: profileID, TargetPath: targetPath, Username: parsed.username, URIPrefix: "", Status: "no_password"}
		return raw, red, &act, nil
	}
	if strings.HasPrefix(parsed.password, "env:") {
		act := makeAction(sourceFile, profileID, "TR-003", targetPath, raw, raw, "", "already_compliant", "uri_already_env")
		red := &uriRedaction{SourceFile: sourceFile, ProfileID: profileID, TargetPath: targetPath, Username: parsed.username, URIPrefix: "", CredRef: strings.TrimPrefix(parsed.password, "env:"), Status: "already_env"}
		return raw, red, &act, nil
	}
	cred, matched := matchCredential(parsed, creds)
	if !matched {
		act := makeAction(sourceFile, profileID, "TR-003", targetPath, raw, raw, "", "already_compliant", "uri_unmapped")
		red := &uriRedaction{SourceFile: sourceFile, ProfileID: profileID, TargetPath: targetPath, Username: parsed.username, URIPrefix: "", Status: "unmapped_credential"}
		return raw, red, &act, nil
	}
	newURI := parsed.scheme + "://" + parsed.username + ":env:" + cred.CredRef + "@" + parsed.hostPort + parsed.path + parsed.query + parsed.fragment
	act := makeAction(sourceFile, profileID, "TR-003", targetPath, raw, newURI, "", "applied", "uri_redacted")
	red := &uriRedaction{SourceFile: sourceFile, ProfileID: profileID, TargetPath: targetPath, Username: parsed.username, URIPrefix: cred.URIPrefix, CredRef: cred.CredRef, Status: "redacted"}
	return newURI, red, &act, nil
}

type parsedURI struct {
	scheme       string
	username     string
	password     string
	hostPort     string
	path         string
	query        string
	fragment     string
	hasPassword  bool
	unsupported  bool
	decodedUser  string
	credFree     string
}

func parseURI(raw string) (*parsedURI, error) {
	colonIdx := strings.Index(raw, "://")
	if colonIdx < 0 {
		return &parsedURI{unsupported: true}, nil
	}
	scheme := strings.ToLower(raw[:colonIdx])
	if scheme != "http" && scheme != "https" {
		return &parsedURI{unsupported: true}, nil
	}
	rest := raw[colonIdx+3:]
	p := &parsedURI{scheme: scheme}

	fragIdx := strings.Index(rest, "#")
	if fragIdx >= 0 {
		p.fragment = rest[fragIdx:]
		rest = rest[:fragIdx]
	}
	qIdx := strings.Index(rest, "?")
	if qIdx >= 0 {
		p.query = rest[qIdx:]
		rest = rest[:qIdx]
	}
	slashIdx := strings.Index(rest, "/")
	hostPart := rest
	p.path = ""
	if slashIdx >= 0 {
		hostPart = rest[:slashIdx]
		p.path = rest[slashIdx:]
	}
	atIdx := strings.LastIndex(hostPart, "@")
	if atIdx >= 0 {
		userinfo := hostPart[:atIdx]
		p.hostPort = hostPart[atIdx+1:]
		colonUser := strings.Index(userinfo, ":")
		if colonUser >= 0 {
			p.username = userinfo[:colonUser]
			p.password = userinfo[colonUser+1:]
			p.hasPassword = true
		} else {
			p.username = userinfo
		}
	} else {
		p.hostPort = hostPart
	}
	p.decodedUser, _ = url.PathUnescape(p.username)
	p.credFree = scheme + "://" + p.hostPort + p.path + p.query + p.fragment
	return p, nil
}

func matchCredential(p *parsedURI, creds []credMapRow) (credMapRow, bool) {
	var matches []credMapRow
	for _, c := range creds {
		decodedCredUser, _ := url.PathUnescape(c.Username)
		if p.decodedUser != decodedCredUser && p.username != c.Username && p.decodedUser != c.Username {
			continue
		}
		if credRowMatches(p, c) {
			matches = append(matches, c)
		}
	}
	if len(matches) == 0 {
		return credMapRow{}, false
	}
	sort.SliceStable(matches, func(i, j int) bool {
		if len(matches[i].URIPrefix) != len(matches[j].URIPrefix) {
			return len(matches[i].URIPrefix) > len(matches[j].URIPrefix)
		}
		return matches[i].RowIndex > matches[j].RowIndex
	})
	return matches[0], true
}

func credRowMatches(p *parsedURI, c credMapRow) bool {
	switch c.MatchMode {
	case "exact_host":
		hostPrefix := p.scheme + "://" + p.hostPort
		return hostPrefix == c.URIPrefix || c.URIPrefix == hostPrefix
	default:
		return strings.HasPrefix(p.credFree, c.URIPrefix)
	}
}

func applyRT004(ctx *profileContext, rel string) ([]policyAction, []exceptionResolution, error) {
	profileID := ctx.info.WorkspaceID
	var actions []policyAction
	var allRes []exceptionResolution

	type rtTarget struct {
		path string
		old  string
		te   *trackingExpInfo
	}
	var targets []rtTarget
	for i := range ctx.tracking.Experiments {
		te := &ctx.tracking.Experiments[i]
		tp := fmt.Sprintf("experiments[id=%s].retention.class", escapeTargetID(te.ID))
		old := ""
		if te.HasClass {
			old = te.RetentionClass
		}
		targets = append(targets, rtTarget{path: tp, old: old, te: te})
	}
	sort.Slice(targets, func(i, j int) bool { return targets[i].path < targets[j].path })

	for _, t := range targets {
		ts := targetScope{ExperimentID: t.te.ID}
		candidates, res := resolveExceptions(ctx, "RT-004", t.path, ts)
		allRes = append(allRes, res...)

		if t.te.RetentionOverride && !t.te.HasClass {
			continue
		}

		desired, err := computeRetentionDesired(ctx, t.te, candidates)
		if err != nil {
			return nil, nil, err
		}

		exID := ""
		reason := "retention_lattice"
		if len(candidates) > 0 {
			exID = candidates[0].ExceptionID
			reason = "winning_exception"
		}

		actions = append(actions, skippedConflictActions(rel, profileID, "RT-004", t.path, t.old, candidates)...)
		status := "applied"
		if t.old == desired {
			status = "already_compliant"
		} else {
			ret := ensureMap(t.te.Raw, "retention")
			ret["class"] = desired
			t.te.RetentionClass = desired
			t.te.HasClass = true
		}
		actions = append(actions, makeAction(rel, profileID, "RT-004", t.path, t.old, desired, exID, status, reason))
	}

	b, err := marshalYAML(ctx.trackYAML)
	if err != nil {
		return nil, nil, err
	}
	ctx.info.Files[rel] = b
	return actions, allRes, nil
}

func computeRetentionDesired(ctx *profileContext, te *trackingExpInfo, candidates []exceptionRow) (string, error) {
	best := ""
	bestRank := -1
	consider := func(class string) error {
		if class == "" {
			return nil
		}
		r, ok := ctx.retention[class]
		if !ok {
			return fmt.Errorf("retention class %q not in lattice", class)
		}
		if r > bestRank {
			bestRank = r
			best = class
		}
		return nil
	}

	if te.RetentionOverride && te.HasClass {
		if err := consider(te.RetentionClass); err != nil {
			return "", err
		}
		if len(candidates) > 0 {
			if err := consider(candidates[0].GrantValue); err != nil {
				return "", err
			}
		}
		if best == "" {
			return te.RetentionClass, nil
		}
		return best, nil
	}

	if err := consider(ctx.info.DefaultRetention); err != nil {
		return "", err
	}
	if exp, ok := ctx.experiments[te.ID]; ok && exp.RetentionClass != "" {
		if err := consider(exp.RetentionClass); err != nil {
			return "", err
		}
	}
	if te.HasClass {
		if err := consider(te.RetentionClass); err != nil {
			return "", err
		}
	}
	for _, c := range candidates {
		if err := consider(c.GrantValue); err != nil {
			return "", err
		}
	}
	if best == "" {
		return ctx.info.DefaultRetention, nil
	}
	return best, nil
}

func applyLG005(ctx *profileContext, rel string) ([]policyAction, []exceptionResolution, []lineageEdge, error) {
	profileID := ctx.info.WorkspaceID
	var actions []policyAction
	var lineage []lineageEdge

	type lgTarget struct {
		path  string
		old   string
		model *modelInfo
	}
	var targets []lgTarget
	for i := range ctx.models {
		m := &ctx.models[i]
		if m.ExperimentID == "" {
			continue
		}
		tp := fmt.Sprintf("models[name=%s].lineage.experiment_id", escapeTargetID(m.Name))
		targets = append(targets, lgTarget{path: tp, old: m.ExperimentID, model: m})
	}
	sort.Slice(targets, func(i, j int) bool { return targets[i].path < targets[j].path })

	for _, t := range targets {
		exp, present := ctx.experiments[t.old]
		expQuarantined := present && exp.Quarantine
		newVal := t.old
		status := "already_compliant"
		reason := "lineage_ok"
		modelQuarantineAfter := t.model.Quarantine

		if !present {
			newVal = ""
			status = "applied"
			reason = "lineage_missing_experiment"
			setModelQuarantine(t.model.Raw, true)
			modelQuarantineAfter = true
		} else if expQuarantined {
			status = "applied"
			reason = "lineage_quarantined_experiment"
			setModelQuarantine(t.model.Raw, true)
			modelQuarantineAfter = true
		}

		actions = append(actions, makeAction(rel, profileID, "LG-005", t.path, t.old, newVal, "", status, reason))
		lineage = append(lineage, lineageEdge{
			ProfileID: profileID, ModelName: t.model.Name, ExperimentID: t.old,
			ExperimentPresent: present, ExperimentQuarantined: expQuarantined,
			ModelQuarantinedAfter: modelQuarantineAfter,
		})
	}

	b, err := marshalDeterministicTOML(ctx.registry)
	if err != nil {
		return nil, nil, nil, err
	}
	ctx.info.Files[rel] = b
	return actions, nil, lineage, nil
}

func setModelQuarantine(m map[string]any, val bool) {
	if gov, ok := m["governance"].(map[string]any); ok {
		gov["quarantine"] = val
		return
	}
	if _, ok := m["governance.quarantine"]; ok {
		m["governance.quarantine"] = val
		return
	}
	m["governance"] = map[string]any{"quarantine": val}
}

func marshalYAML(v any) ([]byte, error) {
	var buf bytes.Buffer
	enc := yaml.NewEncoder(&buf)
	enc.SetIndent(2)
	if err := enc.Encode(v); err != nil {
		return nil, err
	}
	enc.Close()
	out := buf.Bytes()
	if len(out) == 0 || out[len(out)-1] != '\n' {
		out = append(out, '\n')
	}
	return out, nil
}

func marshalDeterministicTOML(root map[string]any) ([]byte, error) {
	ordered := make(map[string]any)
	for _, k := range topTOMLKeys {
		if v, ok := root[k]; ok {
			ordered[k] = v
		}
	}
	var unknown []string
	for k := range root {
		found := false
		for _, kk := range topTOMLKeys {
			if k == kk {
				found = true
				break
			}
		}
		if !found {
			unknown = append(unknown, k)
		}
	}
	sort.Strings(unknown)
	for _, k := range unknown {
		ordered[k] = root[k]
	}
	return toml.Marshal(ordered)
}

func evidenceChainDigest(actions []policyAction) string {
	h := sha256.New()
	for _, a := range actions {
		ex := "<NULL>"
		if a.ExceptionID != "" {
			ex = a.ExceptionID
		}
		parts := []string{a.SourceFile, a.ProfileID, a.RuleID, a.TargetPath, a.OldValue, a.NewValue, ex, a.Status, a.ReasonCode}
		io.WriteString(h, strings.Join(parts, "\x1f"))
		io.WriteString(h, "\n")
	}
	return hex.EncodeToString(h.Sum(nil))
}

func writeEvidence(path string, dossier []byte, inputDigest, outputDigest string, profileCount int, actions []policyAction, resolutions []exceptionResolution, redactions []uriRedaction, lineage []lineageEdge) error {
	_ = os.Remove(path)
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return err
	}
	defer db.Close()

	schema := `
CREATE TABLE policy_actions (
  action_id INTEGER PRIMARY KEY,
  source_file TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  rule_id TEXT NOT NULL,
  target_path TEXT NOT NULL,
  old_value TEXT NOT NULL,
  new_value TEXT NOT NULL,
  exception_id TEXT NULL,
  status TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  value_digest TEXT NOT NULL
);
CREATE TABLE exception_resolution (
  resolution_id INTEGER PRIMARY KEY,
  profile_id TEXT NOT NULL,
  source_doc TEXT NOT NULL,
  source_ordinal INTEGER NOT NULL,
  exception_id TEXT NOT NULL,
  rule_id TEXT NOT NULL,
  target_path TEXT NOT NULL,
  scope_class TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  amendment_seq INTEGER NOT NULL,
  resolution_status TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  precedence_key TEXT NOT NULL
);
CREATE TABLE uri_redactions (
  redaction_id INTEGER PRIMARY KEY,
  source_file TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  target_path TEXT NOT NULL,
  username TEXT NOT NULL,
  uri_prefix TEXT NOT NULL,
  cred_ref TEXT NULL,
  status TEXT NOT NULL
);
CREATE TABLE lineage_edges (
  edge_id INTEGER PRIMARY KEY,
  profile_id TEXT NOT NULL,
  model_name TEXT NOT NULL,
  experiment_id TEXT NOT NULL,
  experiment_present INTEGER NOT NULL,
  experiment_quarantined INTEGER NOT NULL,
  model_quarantined_after INTEGER NOT NULL
);
CREATE TABLE run_summary (
  dossier_digest TEXT NOT NULL,
  input_configs_digest TEXT NOT NULL,
  output_configs_digest TEXT NOT NULL,
  evidence_chain_digest TEXT NOT NULL,
  profile_count INTEGER NOT NULL,
  action_count INTEGER NOT NULL,
  exception_resolution_count INTEGER NOT NULL,
  uri_redaction_count INTEGER NOT NULL,
  lineage_edge_count INTEGER NOT NULL
);`
	if _, err := db.Exec(schema); err != nil {
		return err
	}

	chainDigest := evidenceChainDigest(actions)
	dossierDigest := hex.EncodeToString(sha256Sum(dossier))

	for i, a := range actions {
		var ex any
		if a.ExceptionID != "" {
			ex = a.ExceptionID
		}
		dig := valueDigest(a.RuleID, a.TargetPath, a.OldValue, a.NewValue, a.Status)
		if _, err := db.Exec(`INSERT INTO policy_actions (action_id, source_file, profile_id, rule_id, target_path, old_value, new_value, exception_id, status, reason_code, value_digest) VALUES (?,?,?,?,?,?,?,?,?,?,?)`,
			i+1, a.SourceFile, a.ProfileID, a.RuleID, a.TargetPath, a.OldValue, a.NewValue, ex, a.Status, a.ReasonCode, dig); err != nil {
			return err
		}
	}
	for i, r := range resolutions {
		if _, err := db.Exec(`INSERT INTO exception_resolution (resolution_id, profile_id, source_doc, source_ordinal, exception_id, rule_id, target_path, scope_class, scope_id, amendment_seq, resolution_status, reason_code, precedence_key) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`,
			i+1, r.ProfileID, r.SourceDoc, r.SourceOrdinal, r.ExceptionID, r.RuleID, r.TargetPath, r.ScopeClass, r.ScopeID, r.AmendmentSeq, r.ResolutionStatus, r.ReasonCode, r.PrecedenceKey); err != nil {
			return err
		}
	}
	for i, r := range redactions {
		var cred any
		if r.CredRef != "" {
			cred = r.CredRef
		}
		if _, err := db.Exec(`INSERT INTO uri_redactions (redaction_id, source_file, profile_id, target_path, username, uri_prefix, cred_ref, status) VALUES (?,?,?,?,?,?,?,?)`,
			i+1, r.SourceFile, r.ProfileID, r.TargetPath, r.Username, r.URIPrefix, cred, r.Status); err != nil {
			return err
		}
	}
	for i, e := range lineage {
		if _, err := db.Exec(`INSERT INTO lineage_edges (edge_id, profile_id, model_name, experiment_id, experiment_present, experiment_quarantined, model_quarantined_after) VALUES (?,?,?,?,?,?,?)`,
			i+1, e.ProfileID, e.ModelName, e.ExperimentID, boolInt(e.ExperimentPresent), boolInt(e.ExperimentQuarantined), boolInt(e.ModelQuarantinedAfter)); err != nil {
			return err
		}
	}
	_, err = db.Exec(`INSERT INTO run_summary (dossier_digest, input_configs_digest, output_configs_digest, evidence_chain_digest, profile_count, action_count, exception_resolution_count, uri_redaction_count, lineage_edge_count) VALUES (?,?,?,?,?,?,?,?,?)`,
		dossierDigest, inputDigest, outputDigest, chainDigest, profileCount, len(actions), len(resolutions), len(redactions), len(lineage))
	return err
}

func sha256Sum(b []byte) []byte {
	s := sha256.Sum256(b)
	return s[:]
}

func boolInt(v bool) int {
	if v {
		return 1
	}
	return 0
}
