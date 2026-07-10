package metrics

import "math"

// RoundTo4 rounds a float64 to 4 decimal places using standard rounding.
func RoundTo4(v float64) float64 {
	return math.Round(v*10000) / 10000
}

// SafeDiv performs safe floating-point division, returning 0 if denominator is 0.
func SafeDiv(num, denom float64) float64 {
	if denom == 0 {
		return 0
	}
	return num / denom
}

// Rate computes a rate metric: count / total, rounded to 4dp.
func Rate(count, total int) float64 {
	if total == 0 {
		return 0
	}
	return RoundTo4(float64(count) / float64(total))
}
