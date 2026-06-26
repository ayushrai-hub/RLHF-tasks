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
		out[line] = true
	}
	return out, nil
}

func parseTimestamp(raw any) (time.Time, bool) {
	text, ok := raw.(string)
	if !ok || text == "" {
		return time.Time{}, false
	}
	ts, err := time.Parse(time.RFC3339, text)
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
			request.Timestamp.Before(current.Timestamp) ||
			(request.Timestamp.Equal(current.Timestamp) && request.Seq < current.Seq) ||
			(request.Timestamp.Equal(current.Timestamp) && request.Seq == current.Seq && request.Row < current.Row) {
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

		lane := "ship"
		reason := "ready"
		frozen := cfg.RegionFreezes[request.Region]

		if request.Blocked || frozen {
			lane = "hold"
			if request.Blocked {
				reason = "blocked"
			} else {
				reason = "freeze_window"
			}
		} else if request.RiskScore >= thresholdFor(cfg, serviceID) || slices.Contains(cfg.ForcedReviewTypes, request.ChangeType) {
			lane = "review"
			if slices.Contains(cfg.ForcedReviewTypes, request.ChangeType) {
				reason = "change_type"
			} else {
				reason = "risk_score"
			}
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
