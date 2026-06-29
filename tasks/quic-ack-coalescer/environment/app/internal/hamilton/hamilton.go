package hamilton

import (
	"sort"

	"qack/internal/load"
)

type Share struct {
	ConnID      string `json:"conn_id"`
	Weight      int64  `json:"weight"`
	BasisPoints int64  `json:"basis_points"`
}

// Distribute computes Hamilton largest-remainder basis_points (target=10000)
// across conns.
func Distribute(conns []string, weight map[string]int64, anyUrgent bool) ([]Share, string) {
	direction := "FORWARD"
	if anyUrgent {
		direction = "REVERSE"
	}
	ordered := make([]string, len(conns))
	copy(ordered, conns)
	sort.SliceStable(ordered, func(i, j int) bool {
		return load.NumSuffixLess(ordered[i], ordered[j])
	})
	out := make([]Share, len(ordered))
	var total int64
	for _, c := range ordered {
		total += weight[c]
	}
	if total == 0 {
		for i, c := range ordered {
			out[i] = Share{ConnID: c, Weight: 0, BasisPoints: 0}
		}
		return out, direction
	}
	const target int64 = 10000
	// Floor allocation + per-conn remainder.
	type rem struct {
		idx       int
		conn      string
		remainder int64 // weight*target - basis*total, scaled
	}
	remainders := make([]rem, len(ordered))
	var allocated int64
	for i, c := range ordered {
		w := weight[c]
		basis := w * target / total
		r := (w*target)%total
		out[i] = Share{ConnID: c, Weight: w, BasisPoints: basis}
		remainders[i] = rem{i, c, r}
		allocated += basis
	}
	leftover := target - allocated
	if leftover <= 0 {
		return out, direction
	}
	// Pick the leftover-many conns by remainder DESC; tiebreak by direction.
	sort.SliceStable(remainders, func(i, j int) bool {
		if remainders[i].remainder != remainders[j].remainder {
			return remainders[i].remainder > remainders[j].remainder
		}
		if direction == "FORWARD" {
			return load.NumSuffixLess(remainders[i].conn, remainders[j].conn)
		}
		return load.NumSuffixLess(remainders[j].conn, remainders[i].conn)
	})
	for k := int64(0); k < leftover && k < int64(len(remainders)); k++ {
		out[remainders[k].idx].BasisPoints++
	}
	return out, direction
}
