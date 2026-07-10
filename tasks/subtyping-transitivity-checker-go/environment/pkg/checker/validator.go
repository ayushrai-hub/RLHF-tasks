package checker

import (
	"fmt"

	"transitivity-checker/pkg/types"
)

// ValidateRule checks that a rule has all required fields populated.
func ValidateRule(r types.Rule) error {
	if r.RuleID == "" {
		return fmt.Errorf("rule missing rule_id")
	}
	if r.SubType == "" {
		return fmt.Errorf("rule %s missing sub_type", r.RuleID)
	}
	if r.SuperType == "" {
		return fmt.Errorf("rule %s missing super_type", r.RuleID)
	}
	if r.SubType == r.SuperType {
		return fmt.Errorf("rule %s has reflexive subtyping (sub == super)", r.RuleID)
	}
	return nil
}

// ValidateRuleSet checks the entire rule set for consistency.
func ValidateRuleSet(rules []types.Rule) []error {
	var errs []error
	ids := make(map[string]bool)
	for _, r := range rules {
		if err := ValidateRule(r); err != nil {
			errs = append(errs, err)
		}
		if ids[r.RuleID] {
			errs = append(errs, fmt.Errorf("duplicate rule_id: %s", r.RuleID))
		}
		ids[r.RuleID] = true
	}
	return errs
}
