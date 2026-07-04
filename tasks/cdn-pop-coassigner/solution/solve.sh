#!/usr/bin/env bash
set -euo pipefail

BINARY=/app/task_file/optimizer
SRC=/app/task_file/src/main.go

cat > "$SRC" << 'GO'
package main

import (
	"fmt"
	"math"
	"os"
	"sort"
	"strings"
)

const (
	fnvOffset uint64 = 0xcbf29ce484222325
	fnvPrime  uint64 = 0x100000001b3
	numGroups uint64 = 12
)

func fnv1a(s string) uint64 {
	h := fnvOffset
	for i := 0; i < len(s); i++ {
		h ^= uint64(s[i])
		h *= fnvPrime
	}
	return h
}
func groupOf(id string) int { return int(fnv1a("group|"+id) % numGroups) }
func isForbidden(a, b string) bool {
	x, y := a, b
	if a > b {
		x, y = b, a
	}
	return fnv1a("incompat|"+x+"|"+y)%1000 < 8
}

func allStrings(s, key string) []string {
	pat := "\"" + key + "\""
	var out []string
	pos := 0
	for {
		i := strings.Index(s[pos:], pat)
		if i < 0 {
			break
		}
		start := pos + i + len(pat)
		c := strings.Index(s[start:], ":")
		if c < 0 {
			break
		}
		after := start + c + 1
		q1 := strings.Index(s[after:], "\"")
		if q1 < 0 {
			break
		}
		q1a := after + q1 + 1
		q2 := strings.Index(s[q1a:], "\"")
		if q2 < 0 {
			break
		}
		out = append(out, s[q1a:q1a+q2])
		pos = q1a + q2 + 1
	}
	return out
}
func allInts(s, key string) []int64 {
	pat := "\"" + key + "\""
	var out []int64
	pos := 0
	for {
		i := strings.Index(s[pos:], pat)
		if i < 0 {
			break
		}
		start := pos + i + len(pat)
		c := strings.Index(s[start:], ":")
		if c < 0 {
			break
		}
		k := start + c + 1
		for k < len(s) && (s[k] == ' ' || s[k] == '\t') {
			k++
		}
		neg := false
		if k < len(s) && s[k] == '-' {
			neg = true
			k++
		}
		var v int64 = 0
		any := false
		for k < len(s) && s[k] >= '0' && s[k] <= '9' {
			v = v*10 + int64(s[k]-'0')
			k++
			any = true
		}
		if any {
			if neg {
				v = -v
			}
			out = append(out, v)
			pos = k
		} else {
			break
		}
	}
	return out
}

type Rng struct{ st uint64 }

func (r *Rng) nf() float64 {
	r.st = r.st*6364136223846793005 + 1442695040888963407
	return float64((r.st>>32)&0xffffffff) / 4294967296.0
}
func (r *Rng) ni(m int) int { return int(r.nf()*float64(m)) % m }

func readFile(p string) string {
	b, err := os.ReadFile(p)
	if err != nil {
		return ""
	}
	return string(b)
}

func main() {
	inDir := "input_data"
	outDir := "output_data"
	if len(os.Args) >= 3 {
		inDir = os.Args[1]
		outDir = os.Args[2]
	}

	var ids []string
	var load []int64
	for _, line := range strings.Split(readFile(inDir+"/assets.jsonl"), "\n") {
		if !strings.Contains(line, "asset_id") {
			continue
		}
		s := allStrings(line, "asset_id")
		a := allInts(line, "bytes")
		if len(s) == 0 || len(a) == 0 {
			continue
		}
		ids = append(ids, s[0])
		load = append(load, a[0])
	}
	n := len(ids)

	cfg := readFile(inDir + "/pops_config.json")
	bids := allStrings(cfg, "pop_id")
	cap1 := allInts(cfg, "bytes_capacity")
	g := len(bids)

	gid := make([]int, n)
	for i := 0; i < n; i++ {
		gid[i] = groupOf(ids[i])
	}
	forb := make([][]bool, n)
	for i := 0; i < n; i++ {
		forb[i] = make([]bool, n)
	}
	for i := 0; i < n; i++ {
		for j := i + 1; j < n; j++ {
			if isForbidden(ids[i], ids[j]) {
				forb[i][j] = true
				forb[j][i] = true
			}
		}
	}

	// total co-located forbidden pairs for an assignment
	countViol := func(a []int) int64 {
		memb := make([][]int, g)
		for i := 0; i < n; i++ {
			memb[a[i]] = append(memb[a[i]], i)
		}
		var v int64
		for j := 0; j < g; j++ {
			mm := memb[j]
			for x := 0; x < len(mm); x++ {
				for y := x + 1; y < len(mm); y++ {
					if forb[mm[x]][mm[y]] {
						v++
					}
				}
			}
		}
		return v
	}

	assign := make([]int, n)
	a1 := make([]int64, g)
	order := make([]int, n)
	for i := range order {
		order[i] = i
	}
	sort.Slice(order, func(a, b int) bool { return load[order[a]] > load[order[b]] })
	for _, i := range order {
		pref := gid[i] % g
		chosen := pref
		cand := []int{pref}
		for j := 0; j < g; j++ {
			if j != pref {
				cand = append(cand, j)
			}
		}
		for _, c := range cand {
			if a1[c]+load[i] <= cap1[c] {
				chosen = c
				break
			}
		}
		assign[i] = chosen
		a1[chosen] += load[i]
	}

	score := func(a []int) float64 {
		l := make([]int64, g)
		memb := make([][]int, g)
		for i := 0; i < n; i++ {
			l[a[i]] += load[i]
			memb[a[i]] = append(memb[a[i]], i)
		}
		for j := 0; j < g; j++ {
			if l[j] > cap1[j] {
				return -1.0
			}
		}
		var okp, totp, viol int64
		for j := 0; j < g; j++ {
			mm := memb[j]
			L := len(mm)
			totp += int64(L * (L - 1) / 2)
			for x := 0; x < L; x++ {
				for y := x + 1; y < L; y++ {
					if gid[mm[x]] == gid[mm[y]] {
						okp++
					}
					if forb[mm[x]][mm[y]] {
						viol++
					}
				}
			}
		}
		gs := 1.0
		if totp > 0 {
			gs = float64(okp) / float64(totp)
		}
		var ltot, lmax, lmin int64 = 0, l[0], l[0]
		for j := 0; j < g; j++ {
			ltot += l[j]
			if l[j] > lmax {
				lmax = l[j]
			}
			if l[j] < lmin {
				lmin = l[j]
			}
		}
		lbal := 0.0
		if ltot > 0 {
			lbal = 1.0 - float64(lmax-lmin)/float64(ltot)
		}
		base := 0.70*gs + 0.30*lbal
		if viol > 0 {
			f := 1.0
			k := viol
			if k > 5 {
				k = 5
			}
			for t := int64(0); t < k; t++ {
				f *= 0.55
			}
			base *= math.Max(f, 0.20)
		}
		return base
	}

	cur := score(assign)
	curViol := countViol(assign)
	best := append([]int{}, assign...)
	bestsc := cur
	rng := Rng{st: 0x9E3779B97F4A7C15}
	iters := 600000
	T := 0.04
	cool := math.Pow(0.0006/0.04, 1.0/float64(iters))
	for it := 0; it < iters; it++ {
		T *= cool
		i := rng.ni(n)
		old := assign[i]
		ng := rng.ni(g)
		if ng == old {
			continue
		}
		if a1[ng]+load[i] > cap1[ng] {
			continue
		}
		a1[old] -= load[i]
		a1[ng] += load[i]
		assign[i] = ng
		ns := score(assign)
		nViol := countViol(assign)
		// Reject any move that increases the number of co-located forbidden pairs,
		// and any move producing an infeasible (over-capacity) layout.
		if ns < 0 || nViol > curViol {
			a1[ng] -= load[i]
			a1[old] += load[i]
			assign[i] = old
			continue
		}
		if ns >= cur || rng.nf() < math.Exp((ns-cur)/math.Max(T, 1e-6)) {
			cur = ns
			curViol = nViol
			if ns > bestsc {
				bestsc = ns
				best = append([]int{}, assign...)
			}
		} else {
			a1[ng] -= load[i]
			a1[old] += load[i]
			assign[i] = old
		}
	}
	_ = cur

	// Deterministic repair pass: guarantee ZERO co-located forbidden pairs.
	// Relocate one member of every co-located forbidden pair to a capacity-feasible pop
	// that introduces no new forbidden co-location. A zero-violation layout always exists.
	bl := make([]int64, g)
	for i := 0; i < n; i++ {
		bl[best[i]] += load[i]
	}
	conflictFree := func(item, pop int) bool {
		for k := 0; k < n; k++ {
			if best[k] == pop && forb[item][k] {
				return false
			}
		}
		return true
	}
	for pass := 0; pass < n*g+1; pass++ {
		moved := false
		for i := 0; i < n && !moved; i++ {
			for j := i + 1; j < n; j++ {
				if best[i] == best[j] && forb[i][j] {
					// try to relocate i, else j, to a feasible conflict-free pop
					for _, item := range []int{i, j} {
						for c := 0; c < g; c++ {
							if c == best[item] {
								continue
							}
							if bl[c]+load[item] > cap1[c] {
								continue
							}
							if !conflictFree(item, c) {
								continue
							}
							bl[best[item]] -= load[item]
							bl[c] += load[item]
							best[item] = c
							moved = true
							break
						}
						if moved {
							break
						}
					}
					if moved {
						break
					}
				}
			}
		}
		if !moved {
			break
		}
	}
	bestsc = score(best)

	var sb strings.Builder
	for i := 0; i < n; i++ {
		sb.WriteString(fmt.Sprintf("{\"asset_id\": \"%s\", \"pop_id\": \"%s\"}\n", ids[i], bids[best[i]]))
	}
	os.WriteFile(outDir+"/assignment.jsonl", []byte(sb.String()), 0644)
	fmt.Fprintf(os.Stderr, "oracle best %f viol %d\n", bestsc, countViol(best))
}
GO

cd /app/task_file/src && go build -o "$BINARY" .
"$BINARY" "${INPUT_DIR:-/app/task_file/input_data}" "${OUTPUT_DIR:-/app/task_file/output_data}"
echo "Oracle complete."
