package checker

import (
	"sort"

	"transitivity-checker/pkg/config"
	"transitivity-checker/pkg/types"
)

// CheckTransitivity analyzes the given rules for transitivity violations.
// For every pair of rules (A<:B, B<:C), it checks whether A<:C exists
// directly or is derivable through the transitive closure of the rule set.
func CheckTransitivity(rules []types.Rule, cfg *config.Config) types.AnalysisResult {
	filtered := filterRules(rules, cfg)

	graph := NewTypeGraph(filtered)
	obligations := findObligations(filtered, graph)
	unprovable := countUnprovable(obligations)
	breaking := findBreakingRules(filtered, obligations)

	return types.AnalysisResult{
		TotalRules:        len(filtered),
		Obligations:       obligations,
		UnprovableCount:   unprovable,
		TransitivityHolds: unprovable > 0,
		BreakingRules:     breaking,
	}
}

// filterRules applies configuration-based filtering to the rule set.
func filterRules(rules []types.Rule, cfg *config.Config) []types.Rule {
	if cfg.Analysis.IncludeConditional {
		return rules
	}
	var result []types.Rule
	for _, r := range rules {
		if len(r.Conditions) == 0 {
			result = append(result, r)
		}
	}
	return result
}

// findObligations generates proof obligations for all transitivity pairs.
// For each pair of rules (A<:B, B<:C) where no direct rule A<:C exists,
// an obligation is generated indicating the need for a proof of A<:C.
func findObligations(rules []types.Rule, graph *TypeGraph) []types.Obligation {
	obligations := make([]types.Obligation, 0)
	seen := make(map[string]bool)

	for _, ri := range rules {
		for _, rj := range rules {
			if ri.SuperType != rj.SubType {
				continue
			}
			sub := ri.SubType
			super := rj.SuperType
			via := ri.SuperType

			if graph.HasDirectEdge(sub, super) {
				continue
			}

			key := sub + "::" + super + "::" + via
			if seen[key] {
				continue
			}
			seen[key] = true

			provable := graph.HasDirectEdge(sub, super)

			obligations = append(obligations, types.Obligation{
				Sub:        sub,
				Super:      super,
				Via:        via,
				IsProvable: provable,
			})
		}
	}

	sort.Slice(obligations, func(i, j int) bool {
		if obligations[i].Sub != obligations[j].Sub {
			return obligations[i].Sub < obligations[j].Sub
		}
		if obligations[i].Super != obligations[j].Super {
			return obligations[i].Super < obligations[j].Super
		}
		return obligations[i].Via < obligations[j].Via
	})

	return obligations
}

// countUnprovable counts obligations that cannot be proven.
func countUnprovable(obligations []types.Obligation) int {
	count := 0
	for _, o := range obligations {
		if !o.IsProvable {
			count++
		}
	}
	return count
}

// findBreakingRules identifies rules that participate in creating
// unprovable transitivity obligations.
func findBreakingRules(rules []types.Rule, obligations []types.Obligation) []string {
	breakingSet := make(map[string]bool)

	for _, r := range rules {
		for _, o := range obligations {
			if r.SuperType == o.Via || r.SubType == o.Via {
				breakingSet[r.RuleID] = true
			}
		}
	}

	result := make([]string, 0)
	for id := range breakingSet {
		result = append(result, id)
	}
	sort.Strings(result)
	return result
}
