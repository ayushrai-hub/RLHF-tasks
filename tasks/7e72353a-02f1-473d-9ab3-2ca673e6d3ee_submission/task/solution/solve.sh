#!/bin/bash
set -euo pipefail

cat > /opt/change-freeze/bin/change-freeze <<'SH'
#!/bin/bash
set -euo pipefail

case "${1:-}" in
  compile)
    /opt/change-freeze/bin/config_guard
    /opt/change-freeze/bin/build.sh
    /opt/change-freeze/build/change-freeze compile --outdir /var/lib/change-freeze/out
    ;;
  *)
    echo "Usage: $0 compile" >&2
    exit 2
    ;;
esac
SH

cat > /opt/change-freeze/app/output.go <<'GO'
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"sort"
	"time"

	"example.com/freezeengine"
)

func canonicalJSON(v any) ([]byte, error) {
	return json.Marshal(v)
}

func writeOutput(outDir string, plans []freezeengine.ServicePlan) error {
	sort.Slice(plans, func(i, j int) bool {
		return plans[i].ServiceID < plans[j].ServiceID
	})

	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return err
	}

	planPath := outDir + "/plan.json"
	manifestPath := outDir + "/manifest.json"

	payload := map[string]any{
		"generated_at": time.Now().UTC().Format("2006-01-02T15:04:05Z"),
		"services":     plans,
	}
	planBytes, err := canonicalJSON(payload)
	if err != nil {
		return err
	}
	if err := os.WriteFile(planPath, append(planBytes, '\n'), 0o644); err != nil {
		return err
	}

	planFileBytes, err := os.ReadFile(planPath)
	if err != nil {
		return err
	}
	sum := sha256.Sum256(planFileBytes)
	files := map[string]string{
		"plan.json": hex.EncodeToString(sum[:]),
	}
	canonical, err := canonicalJSON(map[string]any{"files": files})
	if err != nil {
		return err
	}
	manifestSum := sha256.Sum256(canonical)
	manifest := map[string]any{
		"files":           files,
		"manifest_sha256": hex.EncodeToString(manifestSum[:]),
	}
	manifestBytes, err := canonicalJSON(manifest)
	if err != nil {
		return err
	}
	return os.WriteFile(manifestPath, append(manifestBytes, '\n'), 0o644)
}
GO

cat > /opt/change-freeze/vendor_templates/freezeengine/config.go <<'GO'
package freezeengine

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
)

func loadConfigMap(path string) (map[string]any, error) {
	bytes, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out map[string]any
	if err := json.Unmarshal(bytes, &out); err != nil {
		return nil, err
	}
	return out, nil
}

func mergeMapKeys(dst, src map[string]any) map[string]any {
	out := map[string]any{}
	for key, value := range dst {
		out[key] = value
	}
	for key, value := range src {
		out[key] = value
	}
	return out
}

func mergeConfig(base, patch map[string]any) map[string]any {
	out := map[string]any{}
	for key, value := range base {
		out[key] = value
	}
	for key, value := range patch {
		switch key {
		case "team_map", "service_class", "class_review_thresholds", "per_service_review_thresholds", "region_freezes":
			baseMap, okBase := out[key].(map[string]any)
			patchMap, okPatch := value.(map[string]any)
			if okBase && okPatch {
				out[key] = mergeMapKeys(baseMap, patchMap)
				continue
			}
		}
		out[key] = value
	}
	return out
}

func LoadEffectiveConfig(basePath string, patchDir string) (Config, error) {
	cfgMap, err := loadConfigMap(basePath)
	if err != nil {
		return Config{}, err
	}

	entries, err := os.ReadDir(patchDir)
	if err != nil {
		return Config{}, err
	}
	names := make([]string, 0, len(entries))
	for _, entry := range entries {
		if filepath.Ext(entry.Name()) == ".json" {
			names = append(names, entry.Name())
		}
	}
	sort.Strings(names)
	for _, name := range names {
		patchMap, err := loadConfigMap(filepath.Join(patchDir, name))
		if err != nil {
			return Config{}, err
		}
		cfgMap = mergeConfig(cfgMap, patchMap)
	}

	bytes, err := json.Marshal(cfgMap)
	if err != nil {
		return Config{}, err
	}
	var cfg Config
	if err := json.Unmarshal(bytes, &cfg); err != nil {
		return Config{}, err
	}
	return cfg, nil
}
GO

cat > /opt/change-freeze/vendor_templates/freezeengine/plan.go <<'GO'
package freezeengine

import (
	"bufio"
	"encoding/json"
	"os"
	"slices"
	"strings"
	"time"
)

func LoadAllowlist(path string) (map[string]bool, error) {
	bytes, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	out := map[string]bool{}
	for _, line := range strings.Split(string(bytes), "\n") {
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

func parseTimestamp(raw any) (time.Time, bool) {
	text, ok := raw.(string)
	if !ok || len(text) != len("2006-01-02T15:04:05Z") {
		return time.Time{}, false
	}
	ts, err := time.Parse("2006-01-02T15:04:05Z", text)
	if err != nil {
		return time.Time{}, false
	}
	return ts.UTC(), true
}

func readString(in map[string]any, key string) string {
	value, ok := in[key].(string)
	if !ok {
		return ""
	}
	return value
}

func readFloat(in map[string]any, key string) float64 {
	value, ok := in[key].(float64)
	if !ok {
		return 0
	}
	return value
}

func readBool(in map[string]any, key string) bool {
	value, ok := in[key].(bool)
	return ok && value
}

func readSeq(in map[string]any) int {
	value, ok := in["seq"].(float64)
	if !ok {
		return 0
	}
	return int(value)
}

func LoadRequests(path string) ([]Request, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	requests := []Request{}
	scanner := bufio.NewScanner(file)
	row := 0
	for scanner.Scan() {
		row++
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		var raw any
		if err := json.Unmarshal([]byte(line), &raw); err != nil {
			continue
		}
		obj, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		ts, ok := parseTimestamp(obj["ts"])
		if !ok {
			continue
		}
		serviceID := readString(obj, "service_id")
		if serviceID == "" {
			continue
		}
		requests = append(requests, Request{
			ServiceID:   serviceID,
			Timestamp:   ts,
			Seq:         readSeq(obj),
			Row:         row,
			RiskScore:   readFloat(obj, "risk_score"),
			ChangeType:  readString(obj, "change_type"),
			Region:      readString(obj, "region"),
			Blocked:     readBool(obj, "blocked"),
			Disabled:    readBool(obj, "disabled"),
			ForceReason: readString(obj, "force_reason"),
		})
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return requests, nil
}

func thresholdFor(cfg Config, serviceID string) float64 {
	if threshold, ok := cfg.PerServiceReviewThresholds[serviceID]; ok {
		return threshold
	}
	if className, ok := cfg.ServiceClass[serviceID]; ok {
		if threshold, ok := cfg.ClassReviewThresholds[className]; ok {
			return threshold
		}
	}
	return cfg.ReviewThreshold
}

func pickLatest(requests []Request) map[string]Request {
	best := map[string]Request{}
	for _, request := range requests {
		current, ok := best[request.ServiceID]
		if !ok ||
			request.Timestamp.After(current.Timestamp) ||
			(request.Timestamp.Equal(current.Timestamp) && request.Seq > current.Seq) ||
			(request.Timestamp.Equal(current.Timestamp) && request.Seq == current.Seq && request.Row > current.Row) {
			best[request.ServiceID] = request
		}
	}
	return best
}

func BuildPlans(cfg Config, allowlist map[string]bool, requests []Request) []ServicePlan {
	best := pickLatest(requests)
	plans := []ServicePlan{}

	for serviceID, request := range best {
		if !allowlist[serviceID] || strings.HasPrefix(serviceID, "svc-internal-") || request.Disabled {
			continue
		}
		if cfg.RegionFreezes[request.Region] && request.ForceReason != "manual_override" {
			continue
		}

		lane := "ship"
		reason := "ready"
		switch {
		case request.Blocked:
			lane = "hold"
			reason = "blocked"
		case slices.Contains(cfg.ForcedReviewTypes, request.ChangeType):
			lane = "review"
			reason = "change_type"
		case request.RiskScore >= thresholdFor(cfg, serviceID):
			lane = "review"
			reason = "risk_score"
		}
		if request.ForceReason == "manual_override" || request.ForceReason == "cleanup" {
			reason = request.ForceReason
		}

		owner := cfg.TeamMap[serviceID]
		if owner == "" {
			owner = "unknown"
		}
		plans = append(plans, ServicePlan{
			ServiceID:        serviceID,
			Lane:             lane,
			OwnerTeam:        owner,
			RequiresApproval: lane != "ship" || request.RiskScore >= cfg.ApprovalRiskScore,
			Reason:           reason,
		})
	}

	return plans
}
GO

/opt/change-freeze/bin/change-freeze compile
