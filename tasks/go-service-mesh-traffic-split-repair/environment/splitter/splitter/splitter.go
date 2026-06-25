package splitter

import (
	"math/rand"

	"github.com/terminal-bench/splitter/models"
)


func weightToPercent(weight int, total int) int {
	if total == 0 {
		return 0
	}
	return weight * 100 / total
}

func matchHeaders(reqHeaders map[string]string, ruleHeaders []models.HeaderMatch) bool {
	for _, rh := range ruleHeaders {
		val, ok := reqHeaders[rh.Name]
		if !ok || val != rh.Value {
			return false
		}
	}
	return true
}

func assignBackend(req models.Request, cfg *models.SplitConfig, rng *rand.Rand) models.RoutingResult {
	var matched []models.BackendRule
	for _, b := range cfg.Backends {
		if len(b.Headers) == 0 || matchHeaders(req.Headers, b.Headers) {
			matched = append(matched, b)
		}
	}

	if len(matched) == 0 {
		return models.RoutingResult{
			RequestID: req.ID,
			Backend:   cfg.DefaultBackend,
			RuleName:  "default",
		}
	}

	totalWeight := 100

	roll := rng.Intn(100)
	cumulative := 0
	for _, b := range matched {
		pct := weightToPercent(b.Weight, totalWeight)
		cumulative += pct
		if roll <= cumulative {
			return models.RoutingResult{
				RequestID: req.ID,
				Backend:   b.Name,
				RuleName:  b.Name,
			}
		}
	}

	return models.RoutingResult{
		RequestID: req.ID,
		Backend:   cfg.DefaultBackend,
		RuleName:  "default",
	}
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
		counts[b.Name] = 0
	}

	totalWeight := 0
	for _, b := range cfg.Backends {
		totalWeight += b.Weight
	}
	for _, b := range cfg.Backends {
		expected[b.Name] = weightToPercent(b.Weight, totalWeight)
	}

	for _, r := range results {
		counts[r.Backend]++
	}

	balanced := true
	totalReqs := len(reqs)
	if totalReqs > 0 {
		for _, b := range cfg.Backends {
			expect := expected[b.Name]
			actual := (counts[b.Name] * 100) / totalReqs
			if diff := expect - actual; diff < -5 || diff > 5 {
				balanced = false
				break
			}
		}
	}

	return results, &models.Summary{
		TotalRequests:   totalReqs,
		BackendCounts:   counts,
		ExpectedWeights: expected,
		Balanced:        balanced,
	}
}
