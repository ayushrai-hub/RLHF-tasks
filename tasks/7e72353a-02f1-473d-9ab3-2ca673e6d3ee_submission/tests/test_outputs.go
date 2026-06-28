package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"regexp"
	"sort"
	"strings"
	"time"
)

const (
	allowlistPath = "/var/spool/change-freeze/inbox/allowlist.txt"
	requestsPath  = "/var/spool/change-freeze/inbox/requests.ndjson"
	policyPath    = "/etc/change-freeze/policy.json"
	patchDir      = "/etc/change-freeze/policy.d"
	patch10Path   = patchDir + "/10_team_patch.json"
	patch20Path   = patchDir + "/20_policy_patch.json"
	patch30Path   = patchDir + "/30_policy_patch.json"
	outDir        = "/var/lib/change-freeze/out"
	planPath      = outDir + "/plan.json"
	manifestPath  = outDir + "/manifest.json"
)

var expectedSHA = map[string]string{
	"allowlist": "2ff19b399dd07b3fa7d5a3d6f7cf810c798b95e196973bf1abb041d920205b36",
	"requests":  "29fe45991a934f63fc5898d3a91c722572c0558b9cdf47b687e22e813b1e0c14",
	"policy":    "9b3c3524f8aef76502ac61a590b7959c451197a9c0485f78bb63ddb0e4b55268",
	"patch10":   "69d6b61f2c1cfdc41a0570b0b303eeaa381e0ff6d8c1e9338445b67adf8e406f",
	"patch20":   "88e0f96f71cd771871baa28c374f41679190f3b198b167b125b3af09b7635124",
	"patch30":   "cf293bb0ee2603d57e00e10788179aaf16e87f7aa92a9005f4efb0b6de76b589",
}

var tsRe = regexp.MustCompile(`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`)

type testCase struct {
	name string
	fn   func() error
}

func main() {
	tests := []testCase{
		{"test_integrity", testIntegrity},
		{"test_inbox_has_edge_cases", testInboxHasEdgeCases},
		{"test_base_outputs_match_expected_semantics", testBaseOutputsMatchExpectedSemantics},
		{"test_allowlist_case_sensitivity", testAllowlistCaseSensitivity},
		{"test_determinism_and_manifest", testDeterminismAndManifest},
		{"test_compact_json_with_single_newline", testCompactJSONWithSingleNewline},
		{"test_generalizes_to_mutated_inputs", testGeneralizesToMutatedInputs},
		{"test_generalizes_to_policy_and_disable_changes", testGeneralizesToPolicyAndDisableChanges},
	}

	for _, tc := range tests {
		if err := tc.fn(); err != nil {
			fmt.Fprintf(os.Stderr, "FAIL %s: %v\n", tc.name, err)
			os.Exit(1)
		}
		fmt.Printf("PASS %s\n", tc.name)
	}
}

func testIntegrity() error {
	checks := map[string]string{
		allowlistPath: expectedSHA["allowlist"],
		requestsPath:  expectedSHA["requests"],
		policyPath:    expectedSHA["policy"],
		patch10Path:   expectedSHA["patch10"],
		patch20Path:   expectedSHA["patch20"],
		patch30Path:   expectedSHA["patch30"],
	}
	for path, want := range checks {
		got, err := shaFile(path)
		if err != nil {
			return err
		}
		if got != want {
			return fmt.Errorf("sha mismatch for %s: got %s want %s", path, got, want)
		}
	}
	return nil
}

func testInboxHasEdgeCases() error {
	raw, err := os.ReadFile(requestsPath)
	if err != nil {
		return err
	}
	lines := strings.Split(string(raw), "\n")
	hasBlank := false
	hasComment := false
	hasOffset := false
	for _, line := range lines {
		if strings.TrimSpace(line) == "" {
			hasBlank = true
		}
		if strings.HasPrefix(strings.TrimLeft(line, " \t"), "#") {
			hasComment = true
		}
		if strings.Contains(line, "+01:00") {
			hasOffset = true
		}
	}
	if !hasBlank || !hasComment || !hasOffset {
		return fmt.Errorf("missing expected edge-case lines in requests file")
	}
	allowRaw, err := os.ReadFile(allowlistPath)
	if err != nil {
		return err
	}
	if !strings.Contains(string(allowRaw), "svc-api # primary rollout lane") {
		return fmt.Errorf("allowlist inline comment missing")
	}
	return nil
}

func testBaseOutputsMatchExpectedSemantics() error {
	if err := runWrapper(); err != nil {
		return err
	}
	return assertPlanMatchesExpected([]string{
		"svc-api",
		"svc-billing",
		"svc-console",
		"svc-data",
		"svc-l10n",
		"svc-search",
	})
}

func testAllowlistCaseSensitivity() error {
	raw, err := os.ReadFile(allowlistPath)
	if err != nil {
		return err
	}
	mutated := strings.Replace(string(raw), "svc-api # primary rollout lane", "SVC-API", 1)
	return withTemporaryFiles(map[string][]byte{
		allowlistPath: []byte(mutated),
	}, func() error {
		if err := runCompiledBinary(); err != nil {
			return err
		}
		return assertPlanMatchesExpected([]string{
			"svc-billing",
			"svc-console",
			"svc-data",
			"svc-l10n",
			"svc-search",
		})
	})
}

func testDeterminismAndManifest() error {
	if err := runWrapper(); err != nil {
		return err
	}
	first, err := loadJSON(planPath)
	if err != nil {
		return err
	}
	if err := runWrapper(); err != nil {
		return err
	}
	second, err := loadJSON(planPath)
	if err != nil {
		return err
	}
	secondMap := second.(map[string]any)
	firstMap := first.(map[string]any)
	secondMap["generated_at"] = firstMap["generated_at"]
	if !reflect.DeepEqual(firstMap, secondMap) {
		return fmt.Errorf("plan output is not deterministic")
	}

	manifestAny, err := loadJSON(manifestPath)
	if err != nil {
		return err
	}
	manifest := manifestAny.(map[string]any)
	if err := requireExactKeys(manifest, "manifest", "files", "manifest_sha256"); err != nil {
		return fmt.Errorf("manifest schema mismatch")
	}
	files, ok := manifest["files"].(map[string]any)
	if !ok || len(files) != 1 {
		return fmt.Errorf("manifest files schema mismatch")
	}
	planSHA, err := shaFile(planPath)
	if err != nil {
		return err
	}
	if files["plan.json"] != planSHA {
		return fmt.Errorf("manifest plan sha mismatch")
	}
	canonical, err := canonicalJSON(map[string]any{"files": files})
	if err != nil {
		return err
	}
	sum := sha256.Sum256(canonical)
	if manifest["manifest_sha256"] != hex.EncodeToString(sum[:]) {
		return fmt.Errorf("manifest canonical sha mismatch")
	}
	return nil
}

func testCompactJSONWithSingleNewline() error {
	if err := runWrapper(); err != nil {
		return err
	}
	for _, path := range []string{planPath, manifestPath} {
		raw, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		if !bytes.HasSuffix(raw, []byte("\n")) || bytes.HasSuffix(raw, []byte("\n\n")) {
			return fmt.Errorf("%s does not end with exactly one newline", path)
		}
		if bytes.Count(raw, []byte("\n")) != 1 {
			return fmt.Errorf("%s has unexpected newline count", path)
		}
		body := bytes.TrimSuffix(raw, []byte("\n"))
		var obj any
		if err := json.Unmarshal(body, &obj); err != nil {
			return err
		}
		if bytes.Contains(body, []byte(": ")) || bytes.Contains(body, []byte(", ")) || bytes.Contains(body, []byte("\n")) || bytes.Contains(body, []byte("\t")) {
			return fmt.Errorf("%s is not compact json", path)
		}
	}
	return nil
}

func testGeneralizesToMutatedInputs() error {
	policy := map[string]any{
		"review_threshold":      0.55,
		"approval_risk_score":   0.81,
		"forced_review_types":   []any{"schema", "ops"},
		"team_map":              map[string]any{"svc-amber": "alpha", "svc-case": "case-team", "svc-freeze-lab": "lab", "svc-hold": "ops", "svc-zeta": "zeta"},
		"service_class":         map[string]any{"svc-amber": "critical", "svc-case": "default", "svc-freeze-lab": "default", "svc-hold": "default", "svc-zeta": "edge"},
		"class_review_thresholds": map[string]any{
			"critical": 0.35,
			"edge":     0.50,
		},
		"per_service_review_thresholds": map[string]any{
			"svc-zeta": 0.62,
		},
		"region_freezes": map[string]any{
			"eu-central-1": true,
		},
	}
	patch10 := map[string]any{
		"team_map": map[string]any{
			"svc-freeze-lab": "freeze-lab",
			"svc-zeta":       "search-zeta",
		},
	}
	patch20 := map[string]any{
		"forced_review_types": []any{"ops"},
		"class_review_thresholds": map[string]any{
			"default": 0.73,
		},
		"per_service_review_thresholds": map[string]any{
			"svc-case": 0.20,
		},
		"region_freezes": map[string]any{
			"us-west-2": true,
		},
	}
	patch30 := map[string]any{
		"service_class": map[string]any{
			"svc-freeze-lab": "critical",
		},
		"team_map": map[string]any{
			"svc-case": "case-sensitive",
		},
	}
	allowlist := strings.Join([]string{
		"# synthetic allowlist",
		"svc-amber",
		"svc-case",
		"svc-freeze-lab",
		"svc-hold",
		"svc-zeta",
		"svc-internal-shadow",
		"",
	}, "\n")
	requests := strings.Join([]string{
		"# synthetic requests",
		"",
		"not-json",
		"[]",
		`{"service_id":"svc-amber","ts":"2026-04-01T10:00:00Z","seq":1,"risk_score":0.10,"change_type":"app","region":"us-east-1"}`,
		`{"service_id":"svc-amber","ts":"2026-04-01T10:00:00Z","seq":1,"risk_score":0.39,"change_type":"app","region":"us-east-1"}`,
		`{"service_id":"svc-case","ts":"2026-04-01T10:05:00Z","seq":"oops","risk_score":0.21,"change_type":"app","region":"us-east-1"}`,
		`{"service_id":"svc-freeze-lab","ts":"2026-04-01T10:06:00Z","seq":1,"risk_score":0.01,"change_type":"app","region":"eu-central-1","force_reason":"manual_override"}`,
		`{"service_id":"svc-hold","ts":"2026-04-01T10:07:00Z","seq":1,"risk_score":0.95,"change_type":"app","region":"us-east-1","blocked":true}`,
		`{"service_id":"svc-zeta","ts":"2026-04-01T10:08:00Z","seq":2,"risk_score":0.61,"change_type":"ops","region":"us-east-1"}`,
		`{"service_id":"svc-zeta","ts":"2026-04-01T10:08:00Z","seq":2,"risk_score":0.64,"change_type":"ops","region":"us-east-1"}`,
		`{"service_id":"svc-zeta","ts":"2026-04-01T10:00:00+01:00","seq":9,"risk_score":0.99,"change_type":"schema","region":"us-east-1"}`,
		`{"service_id":"svc-internal-shadow","ts":"2026-04-01T10:09:00Z","seq":1,"risk_score":0.99,"change_type":"ops","region":"us-east-1"}`,
		"",
	}, "\n")
	overrides := map[string][]byte{
		allowlistPath: []byte(allowlist),
		requestsPath:  []byte(requests),
		policyPath:    mustMarshalIndent(policy),
		patch10Path:   mustMarshalIndent(patch10),
		patch20Path:   mustMarshalIndent(patch20),
		patch30Path:   mustMarshalIndent(patch30),
	}
	return withTemporaryFiles(overrides, func() error {
		if err := runCompiledBinary(); err != nil {
			return err
		}
		return assertPlanMatchesExpected([]string{
			"svc-amber",
			"svc-case",
			"svc-freeze-lab",
			"svc-hold",
			"svc-zeta",
		})
	})
}

func testGeneralizesToPolicyAndDisableChanges() error {
	requests := strings.Join([]string{
		"# disable and freeze mutation",
		`{"service_id":"svc-api","ts":"2026-05-01T09:00:00Z","seq":1,"risk_score":0.90,"change_type":"app","region":"us-east-1"}`,
		`{"service_id":"svc-api","ts":"2026-05-01T09:01:00Z","seq":2,"risk_score":0.10,"change_type":"app","region":"us-east-1","disabled":true}`,
		`{"service_id":"svc-billing","ts":"2026-05-01T09:02:00Z","seq":1,"risk_score":0.41,"change_type":"app","region":"eu-west-1"}`,
		`{"service_id":"svc-console","ts":"2026-05-01T09:03:00Z","seq":1,"risk_score":0.76,"change_type":"app","region":"us-east-1"}`,
		`{"service_id":"svc-data","ts":"2026-05-01T09:04:00Z","seq":1,"risk_score":0.01,"change_type":"app","region":"ap-south-1"}`,
		`{"service_id":"svc-freeze","ts":"2026-05-01T09:05:00Z","seq":1,"risk_score":0.01,"change_type":"app","region":"eu-west-1"}`,
		`{"service_id":"svc-l10n","ts":"2026-05-01T09:06:00Z","seq":1,"risk_score":0.02,"change_type":"ops","region":"us-east-1"}`,
		`{"service_id":"svc-search","ts":"2026-05-01T09:07:00Z","seq":1,"risk_score":0.59,"change_type":"app","region":"us-east-1"}`,
		"",
	}, "\n")
	patch20 := map[string]any{
		"approval_risk_score": 0.58,
		"forced_review_types": []any{"schema", "infra"},
		"region_freezes": map[string]any{
			"eu-west-1": false,
			"us-east-1": true,
		},
		"per_service_review_thresholds": map[string]any{
			"svc-search": 0.58,
		},
	}
	overrides := map[string][]byte{
		requestsPath: []byte(requests),
		patch20Path:  mustMarshalIndent(patch20),
	}
	return withTemporaryFiles(overrides, func() error {
		if err := runCompiledBinary(); err != nil {
			return err
		}
		return assertPlanMatchesExpected([]string{
			"svc-billing",
			"svc-data",
			"svc-freeze",
		})
	})
}

func runWrapper() error {
	for _, path := range []string{planPath, manifestPath} {
		_ = os.Remove(path)
	}
	cmd := exec.Command("/opt/change-freeze/bin/change-freeze", "compile")
	out, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("wrapper run failed: %s", strings.TrimSpace(string(out)))
	}
	if _, err := os.Stat(planPath); err != nil {
		return fmt.Errorf("plan.json was not written to %s", planPath)
	}
	if _, err := os.Stat(manifestPath); err != nil {
		return fmt.Errorf("manifest.json was not written to %s", manifestPath)
	}
	return nil
}

func runCompiledBinary() error {
	for _, path := range []string{planPath, manifestPath} {
		_ = os.Remove(path)
	}
	build := exec.Command("/opt/change-freeze/bin/build.sh")
	if out, err := build.CombinedOutput(); err != nil {
		return fmt.Errorf("build failed: %s", strings.TrimSpace(string(out)))
	}
	cmd := exec.Command("/opt/change-freeze/build/change-freeze", "compile", "--outdir", outDir)
	if out, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("compiled binary run failed: %s", strings.TrimSpace(string(out)))
	}
	if _, err := os.Stat(planPath); err != nil {
		return fmt.Errorf("plan.json was not written to %s", planPath)
	}
	if _, err := os.Stat(manifestPath); err != nil {
		return fmt.Errorf("manifest.json was not written to %s", manifestPath)
	}
	return nil
}

func assertPlanMatchesExpected(expectedIDs []string) error {
	gotAny, err := loadJSON(planPath)
	if err != nil {
		return err
	}
	got := gotAny.(map[string]any)
	if err := requireExactKeys(got, "plan", "generated_at", "services"); err != nil {
		return err
	}
	generatedAt, ok := got["generated_at"].(string)
	if !ok || !tsRe.MatchString(generatedAt) {
		return fmt.Errorf("generated_at format mismatch")
	}
	services, ok := got["services"].([]any)
	if !ok {
		return fmt.Errorf("services should be an array")
	}
	ids := make([]string, 0, len(services))
	for _, itemAny := range services {
		item, ok := itemAny.(map[string]any)
		if !ok {
			return fmt.Errorf("service item is not an object")
		}
		if err := requireExactKeys(item, "service item", "service_id", "lane", "owner_team", "requires_approval", "reason"); err != nil {
			return err
		}
		id, ok := item["service_id"].(string)
		if !ok {
			return fmt.Errorf("service_id should be string")
		}
		ids = append(ids, id)
	}
	sortedIDs := append([]string(nil), ids...)
	sort.Strings(sortedIDs)
	if !reflect.DeepEqual(ids, sortedIDs) {
		return fmt.Errorf("services are not sorted by service_id")
	}
	got["generated_at"] = "__DYNAMIC__"
	expected, err := expectedPlan()
	if err != nil {
		return err
	}
	if !reflect.DeepEqual(got, expected) {
		gotRaw, _ := json.Marshal(got)
		wantRaw, _ := json.Marshal(expected)
		return fmt.Errorf("plan mismatch\n got=%s\nwant=%s", gotRaw, wantRaw)
	}
	if !reflect.DeepEqual(ids, expectedIDs) {
		return fmt.Errorf("service ids mismatch: got=%v want=%v", ids, expectedIDs)
	}
	return nil
}

func expectedPlan() (map[string]any, error) {
	cfg, err := effectiveConfig()
	if err != nil {
		return nil, err
	}
	allowlist, err := parseAllowlist()
	if err != nil {
		return nil, err
	}
	rows, err := parseRequests()
	if err != nil {
		return nil, err
	}
	latest := latestPerService(rows)

	forcedReviewTypes := toStringSlice(cfg["forced_review_types"])
	regionFreezes := toBoolMap(cfg["region_freezes"])
	teamMap := toStringMap(cfg["team_map"])

	services := make([]map[string]any, 0)
	for serviceID, row := range latest {
		if !allowlist[serviceID] || strings.HasPrefix(serviceID, "svc-internal-") {
			continue
		}
		if row.boolValue("disabled") {
			continue
		}
		if regionFreezes[row.stringValue("region")] && row.stringValue("force_reason") != "manual_override" {
			continue
		}

		reason := "ready"
		lane := "ship"
		forceReason := row.stringValue("force_reason")
		switch {
		case row.boolValue("blocked"):
			lane = "hold"
			reason = "blocked"
		case contains(forcedReviewTypes, row.stringValue("change_type")):
			lane = "review"
			reason = "change_type"
		case row.floatValue("risk_score") >= thresholdFor(cfg, serviceID):
			lane = "review"
			reason = "risk_score"
		}
		if forceReason == "manual_override" || forceReason == "cleanup" {
			reason = forceReason
		}

		owner := teamMap[serviceID]
		if owner == "" {
			owner = "unknown"
		}
		services = append(services, map[string]any{
			"service_id":        serviceID,
			"lane":              lane,
			"owner_team":        owner,
			"requires_approval": lane != "ship" || row.floatValue("risk_score") >= floatFromAny(cfg["approval_risk_score"]),
			"reason":            reason,
		})
	}
	sort.Slice(services, func(i, j int) bool {
		return services[i]["service_id"].(string) < services[j]["service_id"].(string)
	})
	out := make([]any, len(services))
	for i, item := range services {
		out[i] = item
	}
	return map[string]any{
		"generated_at": "__DYNAMIC__",
		"services":     out,
	}, nil
}

func effectiveConfig() (map[string]any, error) {
	cfgAny, err := loadJSON(policyPath)
	if err != nil {
		return nil, err
	}
	cfg := cfgAny.(map[string]any)
	entries, err := os.ReadDir(patchDir)
	if err != nil {
		return nil, err
	}
	names := make([]string, 0)
	for _, entry := range entries {
		if filepath.Ext(entry.Name()) == ".json" {
			names = append(names, entry.Name())
		}
	}
	sort.Strings(names)
	for _, name := range names {
		patchAny, err := loadJSON(filepath.Join(patchDir, name))
		if err != nil {
			return nil, err
		}
		patch := patchAny.(map[string]any)
		for key, value := range patch {
			if mergeKey(key) {
				baseMap, okBase := cfg[key].(map[string]any)
				patchMap, okPatch := value.(map[string]any)
				if okBase && okPatch {
					merged := map[string]any{}
					for mk, mv := range baseMap {
						merged[mk] = mv
					}
					for mk, mv := range patchMap {
						merged[mk] = mv
					}
					cfg[key] = merged
					continue
				}
			}
			cfg[key] = value
		}
	}
	return cfg, nil
}

func mergeKey(key string) bool {
	switch key {
	case "team_map", "service_class", "class_review_thresholds", "per_service_review_thresholds", "region_freezes":
		return true
	default:
		return false
	}
}

func parseAllowlist() (map[string]bool, error) {
	raw, err := os.ReadFile(allowlistPath)
	if err != nil {
		return nil, err
	}
	out := map[string]bool{}
	for _, line := range strings.Split(string(raw), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		line = strings.TrimSpace(strings.SplitN(line, "#", 2)[0])
		if line != "" {
			out[line] = true
		}
	}
	return out, nil
}

type rowMap map[string]any

func (r rowMap) stringValue(key string) string {
	if value, ok := r[key].(string); ok {
		return value
	}
	return ""
}

func (r rowMap) boolValue(key string) bool {
	if value, ok := r[key].(bool); ok {
		return value
	}
	return false
}

func (r rowMap) floatValue(key string) float64 {
	return floatFromAny(r[key])
}

func parseRequests() ([]rowMap, error) {
	raw, err := os.ReadFile(requestsPath)
	if err != nil {
		return nil, err
	}
	lines := strings.Split(string(raw), "\n")
	rows := make([]rowMap, 0)
	for idx, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		var obj any
		if err := json.Unmarshal([]byte(line), &obj); err != nil {
			continue
		}
		asMap, ok := obj.(map[string]any)
		if !ok {
			continue
		}
		asMap["__row__"] = float64(idx)
		rows = append(rows, rowMap(asMap))
	}
	return rows, nil
}

func latestPerService(rows []rowMap) map[string]rowMap {
	type ranked struct {
		ts  int64
		seq int
		row int
		rec rowMap
	}
	best := map[string]ranked{}
	for _, row := range rows {
		serviceID := row.stringValue("service_id")
		if serviceID == "" {
			continue
		}
		ts, ok := parseTS(row["ts"])
		if !ok {
			continue
		}
		seq := intFromAny(row["seq"])
		rowIndex := intFromAny(row["__row__"])
		current, exists := best[serviceID]
		if !exists || ts > current.ts || (ts == current.ts && seq > current.seq) || (ts == current.ts && seq == current.seq && rowIndex > current.row) {
			best[serviceID] = ranked{ts: ts, seq: seq, row: rowIndex, rec: row}
		}
	}
	out := map[string]rowMap{}
	for serviceID, ranked := range best {
		out[serviceID] = ranked.rec
	}
	return out
}

func thresholdFor(cfg map[string]any, serviceID string) float64 {
	if perService, ok := cfg["per_service_review_thresholds"].(map[string]any); ok {
		if value, ok := perService[serviceID]; ok {
			return floatFromAny(value)
		}
	}
	if serviceClass, ok := cfg["service_class"].(map[string]any); ok {
		if className, ok := serviceClass[serviceID].(string); ok {
			if classThresholds, ok := cfg["class_review_thresholds"].(map[string]any); ok {
				if value, ok := classThresholds[className]; ok {
					return floatFromAny(value)
				}
			}
		}
	}
	return floatFromAny(cfg["review_threshold"])
}

func loadJSON(path string) (any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var obj any
	if err := json.Unmarshal(raw, &obj); err != nil {
		return nil, err
	}
	return obj, nil
}

func canonicalJSON(obj any) ([]byte, error) {
	return json.Marshal(obj)
}

func shaFile(path string) (string, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:]), nil
}

func withTemporaryFiles(overrides map[string][]byte, fn func() error) error {
	backups := map[string][]byte{}
	for path := range overrides {
		raw, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		backups[path] = raw
	}
	for path, raw := range overrides {
		if err := os.WriteFile(path, raw, 0o644); err != nil {
			return err
		}
	}
	defer func() {
		for path, raw := range backups {
			_ = os.WriteFile(path, raw, 0o644)
		}
	}()
	return fn()
}

func mustMarshalIndent(obj any) []byte {
	raw, err := json.MarshalIndent(obj, "", "  ")
	if err != nil {
		panic(err)
	}
	return append(raw, '\n')
}

func parseTS(value any) (int64, bool) {
	text, ok := value.(string)
	if !ok || !tsRe.MatchString(text) {
		return 0, false
	}
	ts, err := time.Parse("2006-01-02T15:04:05Z", text)
	if err != nil {
		return 0, false
	}
	return ts.UTC().Unix(), true
}

func floatFromAny(value any) float64 {
	if number, ok := value.(float64); ok {
		return number
	}
	return 0
}

func intFromAny(value any) int {
	if number, ok := value.(float64); ok {
		if number == float64(int(number)) {
			return int(number)
		}
	}
	return 0
}

func toStringSlice(value any) []string {
	items, ok := value.([]any)
	if !ok {
		return nil
	}
	out := make([]string, 0, len(items))
	for _, item := range items {
		if text, ok := item.(string); ok {
			out = append(out, text)
		}
	}
	return out
}

func toStringMap(value any) map[string]string {
	raw, ok := value.(map[string]any)
	if !ok {
		return map[string]string{}
	}
	out := map[string]string{}
	for key, item := range raw {
		if text, ok := item.(string); ok {
			out[key] = text
		}
	}
	return out
}

func toBoolMap(value any) map[string]bool {
	raw, ok := value.(map[string]any)
	if !ok {
		return map[string]bool{}
	}
	out := map[string]bool{}
	for key, item := range raw {
		if flag, ok := item.(bool); ok {
			out[key] = flag
		}
	}
	return out
}

func contains(items []string, want string) bool {
	for _, item := range items {
		if item == want {
			return true
		}
	}
	return false
}

func requireExactKeys(obj map[string]any, label string, keys ...string) error {
	if len(obj) != len(keys) {
		return fmt.Errorf("%s key count mismatch: got %d want %d", label, len(obj), len(keys))
	}
	want := map[string]bool{}
	for _, key := range keys {
		want[key] = true
	}
	for key := range obj {
		if !want[key] {
			return fmt.Errorf("%s has unexpected key %s", label, key)
		}
	}
	for _, key := range keys {
		if _, ok := obj[key]; !ok {
			return fmt.Errorf("%s missing key %s", label, key)
		}
	}
	return nil
}
