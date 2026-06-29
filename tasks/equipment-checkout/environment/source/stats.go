package main

import (
	"math"
	"sort"
)

// nearestRank returns the nearest-rank percentile of sorted values.
// rank = ceil(q * n), 1-indexed into sorted slice.
func nearestRank(sorted []float64, q float64) float64 {
	n := len(sorted)
	if n == 0 {
		return 0
	}
	rank := int(math.Ceil(q * float64(n)))
	if rank < 1 {
		rank = 1
	}
	if rank > n {
		rank = n
	}
	return sorted[rank-1]
}

// sortedFloats returns a sorted copy of values.
func sortedFloats(values []float64) []float64 {
	cp := make([]float64, len(values))
	copy(cp, values)
	sort.Float64s(cp)
	return cp
}

// populationStddev computes population standard deviation (divide by N).
func populationStddev(values []float64) float64 {
	n := float64(len(values))
	if n == 0 {
		return 0
	}
	var sum float64
	for _, v := range values {
		sum += v
	}
	mean := sum / n
	var variance float64
	for _, v := range values {
		d := v - mean
		variance += d * d
	}
	variance /= n
	return math.Sqrt(variance)
}

// bankersRound rounds x to the nearest integer using HALF_EVEN (banker's rounding).
func bankersRound(x float64) int64 {
	floor := math.Floor(x)
	frac := x - floor
	if frac < 0.5 {
		return int64(floor)
	} else if frac > 0.5 {
		return int64(math.Ceil(x))
	}
	// exactly 0.5 — round to even
	f := int64(floor)
	if f%2 == 0 {
		return f
	}
	return f + 1
}
