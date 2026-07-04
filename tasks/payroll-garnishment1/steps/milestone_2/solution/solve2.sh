#!/usr/bin/env bash
set -euo pipefail

# v14: project gains a mid-horizon exemption reset and delinquency-driven
# allocation promotion on top of the multi-period arrears carry (anti-cache 0630).

APP_DIR="/app"

# ── round.go ─────────────────────────────────────────────────────────────────
cat > "$APP_DIR/round.go" << 'GOEOF'
package main

// roundHalfEven rounds num/den to the nearest integer with ties going to the
// even value. den must be positive; num may be negative.
func roundHalfEven(num, den int64) int64 {
	neg := num < 0
	n := num
	if neg {
		n = -n
	}
	q := n / den
	r := n % den
	twice := r * 2
	if twice > den || (twice == den && q%2 == 1) {
		q++
	}
	if neg {
		return -q
	}
	return q
}
GOEOF

# ── garnish.go (forward model + one-pool grossup + coupled target-gross) ──────
cat > "$APP_DIR/garnish.go" << 'GOEOF'
package main

import "sort"

// Forward-model constants. All amounts are integer cents.
const (
	minWage30x int64 = 21750  // 30x the 725-cent federal minimum hourly wage
	poolCap    int64 = 200000 // absolute ceiling on the per-period garnishment pool
)

// bracket is one progressive marginal tax band: Rate percent applies to the
// slice of gross from Threshold up to the next band's threshold.
type bracket struct {
	Threshold int64
	Rate      int64
}

// taxBrackets are the fixed marginal bands, ascending by threshold.
var taxBrackets = []bracket{
	{0, 0},
	{50000, 10},
	{200000, 22},
	{500000, 32},
}

// kindFracPct is the per-kind fractional ceiling as a whole percent of
// disposable earnings. A kind not listed falls back to 100 percent, so its
// fractional ceiling never binds and only the order's absolute cap applies.
var kindFracPct = map[string]int64{
	"child-support": 12,
	"tax-levy":      25,
	"creditor":      10,
}

// fracPctFor returns the whole-percent fractional ceiling for a kind.
func fracPctFor(kind string) int64 {
	if p, ok := kindFracPct[kind]; ok {
		return p
	}
	return 100
}

// progressiveTax returns the tax in cents on the gross. Each band's slice
// portion times its whole-percent rate is accumulated in exact cent-percent
// units, then the total is divided by 100 and rounded half to even.
func progressiveTax(gross int64) int64 {
	if gross <= 0 {
		return 0
	}
	var acc int64 // cent-percent units
	for i, b := range taxBrackets {
		if gross <= b.Threshold {
			break
		}
		top := gross
		if i+1 < len(taxBrackets) && taxBrackets[i+1].Threshold < top {
			top = taxBrackets[i+1].Threshold
		}
		acc += (top - b.Threshold) * b.Rate
	}
	return roundHalfEven(acc, 100)
}

// disposableFor returns disposable earnings: gross minus progressive tax,
// floored at zero.
func disposableFor(gross int64) int64 {
	disp := gross - progressiveTax(gross)
	if disp < 0 {
		disp = 0
	}
	return disp
}

// garnishablePool returns the CCPA-capped pool for disposable earnings: the
// smaller of round-half-to-even of 25 percent of disposable and the amount
// disposable exceeds 30x the federal minimum hourly wage, then capped at the
// absolute ceiling.
func garnishablePool(disposable int64) int64 {
	if disposable <= 0 {
		return 0
	}
	limit1 := roundHalfEven(disposable*25, 100)
	limit2 := disposable - minWage30x
	if limit2 < 0 {
		limit2 = 0
	}
	pool := limit1
	if limit2 < pool {
		pool = limit2
	}
	if pool > poolCap {
		pool = poolCap
	}
	return pool
}

// effectiveCap returns the smaller of an order's absolute cap and its
// kind-fractional ceiling at the given disposable.
func effectiveCap(o Order, disposable int64) int64 {
	frac := roundHalfEven(disposable*fracPctFor(o.Kind), 100)
	if frac < o.Cap {
		return frac
	}
	return o.Cap
}

// Net is the one-pool net: disposable minus the whole CCPA pool. It ignores the
// per-order caps and is the inverse target of Grossup.
func Net(gross int64) int64 {
	disp := disposableFor(gross)
	return disp - garnishablePool(disp)
}

// Grossup returns the smallest whole-cent gross whose one-pool Net is at least
// target, by bisection over [target, 4*target] with hi doubling (guard 100) and
// at most 200 narrowing iterations.
func Grossup(target int64) int64 {
	if target <= 0 {
		return 0
	}
	lo := target
	hi := target * 4
	for guard := 0; Net(hi) < target && guard < 100; guard++ {
		hi *= 2
	}
	for it := 0; lo < hi && it < 200; it++ {
		mid := lo + (hi-lo)/2
		if Net(mid) >= target {
			hi = mid
		} else {
			lo = mid + 1
		}
	}
	return lo
}

// OrderAlloc pairs an order with the integer cents allocated to it under the
// layered CCPA allocation at a given disposable and pool.
type OrderAlloc struct {
	Order  Order
	Amount int64
}

// allocateOrders runs the layered priority-waterfall allocation over the orders,
// which must already be ascending by priority then id, and returns the per-order
// withheld cents aligned to that input order. Orders sharing a priority form a
// group funded together against a running remaining pool: when the remaining
// pool covers the group's combined effective caps every order is funded to its
// own effective cap, otherwise the remaining pool is divided across the group in
// proportion to each order's effective cap with largest-remainder rounding (each
// order gets the integer floor of its proportional share, then the leftover
// cents go one each to the largest fractional remainders, ties broken by
// ascending order id) so the integer cents sum exactly to the remaining pool and
// nothing cascades to any junior group.
func allocateOrders(disposable, pool int64, orders []Order) []OrderAlloc {
	res := make([]OrderAlloc, len(orders))
	for i := range orders {
		res[i] = OrderAlloc{Order: orders[i], Amount: 0}
	}
	remaining := pool
	i := 0
	for i < len(orders) && remaining > 0 {
		j := i
		pr := orders[i].Priority
		var sumCaps int64
		for j < len(orders) && orders[j].Priority == pr {
			sumCaps += effectiveCap(orders[j], disposable)
			j++
		}
		if sumCaps <= 0 {
			i = j
			continue
		}
		if remaining >= sumCaps {
			for k := i; k < j; k++ {
				res[k].Amount = effectiveCap(orders[k], disposable)
			}
			remaining -= sumCaps
			i = j
			continue
		}
		// The pool binds within this group: proportional largest-remainder split.
		size := j - i
		base := make([]int64, size)
		rem := make([]int64, size)
		var allocated int64
		for k := 0; k < size; k++ {
			c := effectiveCap(orders[i+k], disposable)
			base[k] = remaining * c / sumCaps
			rem[k] = remaining*c - base[k]*sumCaps
			allocated += base[k]
		}
		leftover := remaining - allocated
		idx := make([]int, size)
		for k := range idx {
			idx[k] = k
		}
		// Stable sort by descending remainder keeps equal remainders in ascending
		// id order, so the leftover cents break ties toward the smaller id.
		sort.SliceStable(idx, func(a, b int) bool {
			return rem[idx[a]] > rem[idx[b]]
		})
		for k := int64(0); k < leftover; k++ {
			base[idx[k]]++
		}
		for k := 0; k < size; k++ {
			res[i+k].Amount = base[k]
		}
		remaining = 0
		i = j
	}
	return res
}

// allocatePool returns the total cents the orders consume from the pool under
// allocateOrders. The total may be strictly below the pool when the capped
// orders cannot absorb it.
func allocatePool(disposable, pool int64, orders []Order) int64 {
	var total int64
	for _, a := range allocateOrders(disposable, pool, orders) {
		total += a.Amount
	}
	return total
}

// MultiNet is the coupled net: disposable minus the part of the CCPA pool the
// priority-ordered, capped orders actually consume. Both the pool and every
// per-order cap are recomputed at this gross.
func MultiNet(gross int64, orders []Order) int64 {
	disp := disposableFor(gross)
	pool := garnishablePool(disp)
	return disp - allocatePool(disp, pool, orders)
}

// TargetGross returns the smallest whole-cent gross whose MultiNet for these
// orders is at least target. It reuses the Grossup bracket and bounds but wraps
// the priority allocation at each candidate gross.
func TargetGross(target int64, orders []Order) int64 {
	if target <= 0 {
		return 0
	}
	lo := target
	hi := target * 4
	for guard := 0; MultiNet(hi, orders) < target && guard < 100; guard++ {
		hi *= 2
	}
	for it := 0; lo < hi && it < 200; it++ {
		mid := lo + (hi-lo)/2
		if MultiNet(mid, orders) >= target {
			hi = mid
		} else {
			lo = mid + 1
		}
	}
	return lo
}
GOEOF

# ── argparse.go helper (positional integer, rejects fractional/empty) ─────────
cat > "$APP_DIR/argparse.go" << 'GOEOF'
package main

import "strconv"

// parseIntArg parses a positional argument as a base-10 integer, rejecting an
// empty, fractional, or non-numeric value.
func parseIntArg(s string) (int64, bool) {
	if s == "" {
		return 0, false
	}
	n, err := strconv.ParseInt(s, 10, 64)
	if err != nil {
		return 0, false
	}
	return n, true
}
GOEOF

# ── period.go (exemption floor, multi-period arrears sim, cap statistics) ─────
cat > "$APP_DIR/period.go" << 'GOEOF'
package main

import "sort"

const (
	exemptStep int64 = 4250 // protected-floor addition per claimed exemption
	arrearsBps int64 = 125  // per-period statutory carry rate on unmet garnishment, in bps
	statsPct   int64 = 75   // nearest-rank percentile reported by stats
)

// poolWithFloor is the CCPA pool with the flat 30x-minimum protected floor
// replaced by an exemption-adjusted floor.
func poolWithFloor(disposable, floor int64) int64 {
	if disposable <= 0 {
		return 0
	}
	limit1 := roundHalfEven(disposable*25, 100)
	limit2 := disposable - floor
	if limit2 < 0 {
		limit2 = 0
	}
	pool := limit1
	if limit2 < pool {
		pool = limit2
	}
	if pool > poolCap {
		pool = poolCap
	}
	return pool
}

// PeriodResult is one order's multi-period outcome: the cents withheld across
// every simulated period and the arrears still owed after the final period.
type PeriodResult struct {
	Order   Order
	Total   int64
	Arrears int64
}

// Project simulates periods consecutive pay periods at a fixed gross, with two
// couplings that tie a period to its history. Disposable is fixed by the gross
// and holds across every period. The protected floor is the flat 30x minimum
// raised by exemptStep per claimed exemption; the pool is the CCPA pool against
// that floor. A mid-horizon reset (hasReset) switches the exemption count from
// exempt to exemptAfter at the start of the resetAt-th period (1-based), so the
// pool refloats from that period on. Each period an order claims its effective
// cap at this disposable plus its carried arrears, but the per-period allocation
// order is delinquency-first: an order whose carried-in arrears are at least its
// own absolute cap is funded ahead of every non-delinquent order regardless of
// stored priority, then by ascending priority then id. Orders sharing the same
// delinquency tier and priority form a group funded together, a binding group
// split pro-rata by largest remainder with ties to the smaller id, and the
// binding group consumes the remaining pool so nothing cascades past it. The
// unmet remainder compounds by arrearsBps, rounded half to even, before the next
// period including after the last. orders must be ascending by priority then id;
// the returned slice keeps that stable print order.
func Project(orders []Order, gross, periods, exempt int64, hasReset bool, resetAt, exemptAfter int64) []PeriodResult {
	disp := disposableFor(gross)
	n := len(orders)
	arrears := make([]int64, n)
	total := make([]int64, n)
	for p := int64(1); p <= periods; p++ {
		ex := exempt
		if hasReset && p >= resetAt {
			ex = exemptAfter
		}
		pool := poolWithFloor(disp, minWage30x+ex*exemptStep)

		claim := make([]int64, n)
		tier := make([]int64, n)
		for k := 0; k < n; k++ {
			claim[k] = effectiveCap(orders[k], disp) + arrears[k]
			if arrears[k] >= orders[k].Cap {
				tier[k] = 0
			} else {
				tier[k] = 1
			}
		}
		// Per-period allocation ranking: delinquency tier, then priority, then id.
		idx := make([]int, n)
		for k := range idx {
			idx[k] = k
		}
		sort.SliceStable(idx, func(a, b int) bool {
			x, y := idx[a], idx[b]
			if tier[x] != tier[y] {
				return tier[x] < tier[y]
			}
			if orders[x].Priority != orders[y].Priority {
				return orders[x].Priority < orders[y].Priority
			}
			return orders[x].ID < orders[y].ID
		})

		alloc := make([]int64, n)
		remaining := pool
		i := 0
		for i < n && remaining > 0 {
			x := idx[i]
			t, pr := tier[x], orders[x].Priority
			j := i
			var sumCaps int64
			for j < n && tier[idx[j]] == t && orders[idx[j]].Priority == pr {
				sumCaps += claim[idx[j]]
				j++
			}
			if sumCaps <= 0 {
				i = j
				continue
			}
			if remaining >= sumCaps {
				for k := i; k < j; k++ {
					alloc[idx[k]] = claim[idx[k]]
				}
				remaining -= sumCaps
				i = j
				continue
			}
			// The pool binds within this group: proportional largest-remainder split.
			size := j - i
			base := make([]int64, size)
			rem := make([]int64, size)
			var allocated int64
			for k := 0; k < size; k++ {
				c := claim[idx[i+k]]
				base[k] = remaining * c / sumCaps
				rem[k] = remaining*c - base[k]*sumCaps
				allocated += base[k]
			}
			leftover := remaining - allocated
			// Group members are already ascending by id, so a stable sort by
			// descending remainder breaks leftover-cent ties toward the smaller id.
			ord := make([]int, size)
			for k := range ord {
				ord[k] = k
			}
			sort.SliceStable(ord, func(a, b int) bool { return rem[ord[a]] > rem[ord[b]] })
			for k := int64(0); k < leftover; k++ {
				base[ord[k]]++
			}
			for k := 0; k < size; k++ {
				alloc[idx[i+k]] = base[k]
			}
			remaining = 0
			i = j
		}

		for k := 0; k < n; k++ {
			total[k] += alloc[k]
			unmet := claim[k] - alloc[k]
			arrears[k] = roundHalfEven(unmet*(10000+arrearsBps), 10000)
		}
	}
	res := make([]PeriodResult, n)
	for k := 0; k < n; k++ {
		res[k] = PeriodResult{Order: orders[k], Total: total[k], Arrears: arrears[k]}
	}
	return res
}

// CapStats are the order-cap summary figures: the count, the nearest-rank
// percentile, the population variance (in cents squared), and the
// round-half-even mean, all integer.
type CapStats struct {
	Count int64
	Pct   int64
	Var   int64
	Mean  int64
}

// OrderStats summarizes the absolute caps of the orders. The percentile is
// nearest-rank at statsPct with a 1-based rank of ceil(p*n/100) over the
// ascending caps, so it is always a stored cap. The variance is the population
// variance n*sumsq-sum^2 over n^2 rounded half to even, dividing by n not n-1.
// The mean is sum over n rounded half to even.
func OrderStats(orders []Order) CapStats {
	n := int64(len(orders))
	if n == 0 {
		return CapStats{}
	}
	xs := make([]int64, n)
	for i, o := range orders {
		xs[i] = o.Cap
	}
	sort.Slice(xs, func(a, b int) bool { return xs[a] < xs[b] })
	var sum, sumsq int64
	for _, x := range xs {
		sum += x
		sumsq += x * x
	}
	mean := roundHalfEven(sum, n)
	variance := roundHalfEven(n*sumsq-sum*sum, n*n)
	rank := (statsPct*n + 99) / 100 // ceil(statsPct*n/100), 1-based
	pct := xs[rank-1]
	return CapStats{Count: n, Pct: pct, Var: variance, Mean: mean}
}
GOEOF

# ── patch cli.go: CmdNet, CmdGrossup, CmdTargetGross ─────────────────────────
python3 - "$APP_DIR/cli.go" << 'PYEOF'
import sys
path = sys.argv[1]
src = open(path).read()

def replace_func(src, name, new_func):
    start = src.index(f"func {name}(")
    i = src.index("{", start)
    depth = 0
    j = i
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return src[:start] + new_func.strip() + src[j + 1:]

cmd_net = '''
func CmdNet(args []string) {
	flags, pos, err := splitFlags(args, map[string]bool{})
	_ = flags
	if err != nil || len(pos) != 1 {
		badInput()
	}
	gross, ok := parseIntArg(pos[0])
	if !ok || gross < 0 {
		badInput()
	}
	fmt.Println(Net(gross))
}
'''

cmd_grossup = '''
func CmdGrossup(args []string) {
	flags, pos, err := splitFlags(args, map[string]bool{})
	_ = flags
	if err != nil || len(pos) != 1 {
		badInput()
	}
	target, ok := parseIntArg(pos[0])
	if !ok || target < 0 {
		badInput()
	}
	fmt.Println(Grossup(target))
}
'''

cmd_target = '''
func CmdTargetGross(args []string) {
	flags, pos, err := splitFlags(args, map[string]bool{})
	_ = flags
	if err != nil || len(pos) != 2 {
		badInput()
	}
	e := requireEmployee(pos[0])
	target, ok := parseIntArg(pos[1])
	if !ok || target < 0 {
		badInput()
	}
	orders, err := ListOrders(e.ID)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(TargetGross(target, orders))
}
'''

cmd_allocate = '''
func CmdAllocate(args []string) {
	flags, pos, err := splitFlags(args, map[string]bool{})
	_ = flags
	if err != nil || len(pos) != 2 {
		badInput()
	}
	e := requireEmployee(pos[0])
	gross, ok := parseIntArg(pos[1])
	if !ok || gross < 0 {
		badInput()
	}
	orders, err := ListOrders(e.ID)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	disp := disposableFor(gross)
	pool := garnishablePool(disp)
	for _, a := range allocateOrders(disp, pool, orders) {
		fmt.Printf("%d %s %d\\n", a.Order.ID, a.Order.Kind, a.Amount)
	}
}
'''

cmd_project = '''
func CmdProject(args []string) {
	flags, pos, err := splitFlags(args, map[string]bool{
		"--gross": true, "--periods": true, "--exempt": true,
		"--reset": true, "--exempt-after": true,
	})
	if err != nil || len(pos) != 1 {
		badInput()
	}
	e := requireEmployee(pos[0])
	gross, okG := parseIntFlag(flags, "--gross")
	periods, okP := parseIntFlag(flags, "--periods")
	if !okG || gross <= 0 || !okP || periods <= 0 {
		badInput()
	}
	exempt := int64(0)
	if _, has := flags["--exempt"]; has {
		v, okE := parseIntFlag(flags, "--exempt")
		if !okE || v < 0 {
			badInput()
		}
		exempt = v
	}
	_, hasR := flags["--reset"]
	_, hasA := flags["--exempt-after"]
	if hasR != hasA {
		badInput()
	}
	hasReset := false
	var resetAt, exemptAfter int64
	if hasR {
		r, okR := parseIntFlag(flags, "--reset")
		a, okA := parseIntFlag(flags, "--exempt-after")
		if !okR || r <= 0 || !okA || a < 0 {
			badInput()
		}
		hasReset, resetAt, exemptAfter = true, r, a
	}
	orders, err := ListOrders(e.ID)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	for _, r := range Project(orders, gross, periods, exempt, hasReset, resetAt, exemptAfter) {
		fmt.Printf("%d %s %d %d\\n", r.Order.ID, r.Order.Kind, r.Total, r.Arrears)
	}
}
'''

cmd_stats = '''
func CmdStats(args []string) {
	flags, pos, err := splitFlags(args, map[string]bool{})
	_ = flags
	if err != nil || len(pos) != 1 {
		badInput()
	}
	e := requireEmployee(pos[0])
	orders, err := ListOrders(e.ID)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	s := OrderStats(orders)
	fmt.Printf("%d %d %d %d\\n", s.Count, s.Pct, s.Var, s.Mean)
}
'''

src = replace_func(src, "CmdNet", cmd_net)
src = replace_func(src, "CmdGrossup", cmd_grossup)
src = replace_func(src, "CmdTargetGross", cmd_target)
src = replace_func(src, "CmdAllocate", cmd_allocate)
src = replace_func(src, "CmdProject", cmd_project)
src = replace_func(src, "CmdStats", cmd_stats)
open(path, "w").write(src)
PYEOF

cd "$APP_DIR"
gofmt -w round.go garnish.go argparse.go period.go cli.go
go build -o /app/pay .
echo "Build successful: /app/pay"
