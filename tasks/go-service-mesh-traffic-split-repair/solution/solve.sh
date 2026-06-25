#!/bin/bash
set +H
set -euo pipefail
export PATH="/usr/local/go/bin:${PATH}"

cat > /app/environment/splitter/models/models.go <<'GOEOF'
package models

type HeaderMatch struct {
	Name  string `json:"name"`
	Value string `json:"value,omitempty"`
	Mode  string `json:"mode,omitempty"`
}

type BackendRule struct {
	Name    string        `json:"name"`
	Weight  int           `json:"weight"`
	Headers []HeaderMatch `json:"headers,omitempty"`
	Enabled *bool         `json:"enabled,omitempty"`
}

type SplitConfig struct {
	DefaultBackend string        `json:"default_backend"`
	Backends       []BackendRule `json:"backends"`
}

type Request struct {
	ID      string            `json:"id"`
	Headers map[string]string `json:"headers"`
}

type RoutingResult struct {
	RequestID string `json:"request_id"`
	Backend   string `json:"backend"`
	RuleName  string `json:"rule_name"`
}

type Summary struct {
	TotalRequests   int            `json:"total_requests"`
	BackendCounts   map[string]int `json:"backend_counts"`
	ExpectedWeights map[string]int `json:"expected_weights"`
	Balanced        bool           `json:"balanced"`
}

type OutputReport struct {
	RoutedRequests []RoutingResult `json:"routed_requests"`
	Summary        Summary         `json:"summary"`
}
GOEOF

cat > /app/environment/splitter/splitter/splitter.go <<'GOEOF'
package splitter

import (
	"math/rand"
	"strings"

	"github.com/terminal-bench/splitter/models"
)

func enabled(rule models.BackendRule) bool {
	return rule.Enabled == nil || *rule.Enabled
}

func findHeader(reqHeaders map[string]string, name string) (string, bool) {
	for k, v := range reqHeaders {
		if strings.EqualFold(k, name) {
			return v, true
		}
	}
	return "", false
}

func containsToken(headerValue, want string) bool {
	for _, part := range strings.Split(headerValue, ",") {
		if strings.TrimSpace(part) == want {
			return true
		}
	}
	return false
}

func matchOneHeader(reqHeaders map[string]string, rh models.HeaderMatch) bool {
	mode := rh.Mode
	if mode == "" {
		mode = "exact"
	}
	val, ok := findHeader(reqHeaders, rh.Name)
	switch mode {
	case "exact":
		return ok && val == rh.Value
	case "contains-token":
		return ok && containsToken(val, rh.Value)
	case "absent":
		return !ok
	default:
		return false
	}
}

func matchHeaders(reqHeaders map[string]string, ruleHeaders []models.HeaderMatch) bool {
	for _, rh := range ruleHeaders {
		if !matchOneHeader(reqHeaders, rh) {
			return false
		}
	}
	return true
}

func assignBackend(req models.Request, cfg *models.SplitConfig, rng *rand.Rand) models.RoutingResult {
	matched := make([]models.BackendRule, 0, len(cfg.Backends))
	for _, b := range cfg.Backends {
		if !enabled(b) || b.Weight <= 0 {
			continue
		}
		if len(b.Headers) == 0 || matchHeaders(req.Headers, b.Headers) {
			matched = append(matched, b)
		}
	}

	if len(matched) == 0 {
		return models.RoutingResult{RequestID: req.ID, Backend: cfg.DefaultBackend, RuleName: "default"}
	}

	totalWeight := 0
	for _, b := range matched {
		totalWeight += b.Weight
	}
	roll := rng.Intn(totalWeight)
	cumulative := 0
	for _, b := range matched {
		cumulative += b.Weight
		if roll < cumulative {
			return models.RoutingResult{RequestID: req.ID, Backend: b.Name, RuleName: b.Name}
		}
	}
	return models.RoutingResult{RequestID: req.ID, Backend: cfg.DefaultBackend, RuleName: "default"}
}

func RouteRequests(reqs []models.Request, cfg *models.SplitConfig, seed int64) ([]models.RoutingResult, *models.Summary) {
	rng := rand.New(rand.NewSource(seed))
	results := make([]models.RoutingResult, len(reqs))
	for i, req := range reqs {
		results[i] = assignBackend(req, cfg, rng)
	}

	counts := make(map[string]int)
	expected := make(map[string]int)
	for _, b := range cfg.Backends {
		if enabled(b) && b.Weight > 0 {
			counts[b.Name] = 0
			expected[b.Name] = b.Weight
		}
	}
	for _, r := range results {
		counts[r.Backend]++
	}

	balanced := true
	totalReqs := len(reqs)
	if totalReqs > 0 {
		totalWeight := 0
		for _, w := range expected {
			totalWeight += w
		}
		if totalWeight > 0 {
			for name, weight := range expected {
				expect := (weight * 100) / totalWeight
				actual := (counts[name] * 100) / totalReqs
				if diff := expect - actual; diff < -5 || diff > 5 {
					balanced = false
					break
				}
			}
		}
	}

	return results, &models.Summary{TotalRequests: totalReqs, BackendCounts: counts, ExpectedWeights: expected, Balanced: balanced}
}
GOEOF

gofmt -w /app/environment/splitter/models/models.go /app/environment/splitter/splitter/splitter.go
mkdir -p /app/bin /app/output
cd /app/environment/splitter
go build -o /app/bin/splitter .
SEED=7 /app/bin/splitter
