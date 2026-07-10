package output

import (
	"fmt"
	"strings"

	"transitivity-checker/pkg/types"
)

// FormatObligation returns a human-readable string for an obligation.
func FormatObligation(o types.Obligation) string {
	status := "provable"
	if !o.IsProvable {
		status = "UNPROVABLE"
	}
	return fmt.Sprintf("%s <: %s (via %s) [%s]", o.Sub, o.Super, o.Via, status)
}

// FormatBreakingRules returns a formatted list of breaking rules.
func FormatBreakingRules(rules []string) string {
	if len(rules) == 0 {
		return "none"
	}
	return strings.Join(rules, ", ")
}
