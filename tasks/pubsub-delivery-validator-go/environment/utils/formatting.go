package utils

import (
	"fmt"
	"math"
)

// FormatRate rounds a float to 4 decimal places for report output.
func FormatRate(v float64) float64 {
	return math.Round(v*10000) / 10000
}

// FormatViolation produces a human-readable violation summary string.
func FormatViolation(vtype, deliveryID, details string) string {
	return fmt.Sprintf("[%s] %s: %s", vtype, deliveryID, details)
}

// FormatPriority returns a human-readable priority label.
func FormatPriority(p int) string {
	switch {
	case p >= 3:
		return "HIGH"
	case p >= 2:
		return "MEDIUM"
	default:
		return "LOW"
	}
}
