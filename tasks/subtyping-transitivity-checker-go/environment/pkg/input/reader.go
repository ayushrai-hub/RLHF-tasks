package input

import (
	"encoding/json"
	"os"
	"sort"

	"transitivity-checker/pkg/types"
)

// ReadRules reads and parses the subtyping rules from a JSON file.
// Rules are returned sorted by rule_id for deterministic processing.
func ReadRules(path string) ([]types.Rule, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var rules []types.Rule
	if err := json.Unmarshal(data, &rules); err != nil {
		return nil, err
	}

	sort.Slice(rules, func(i, j int) bool {
		return rules[i].RuleID < rules[j].RuleID
	})

	return rules, nil
}
