#!/usr/bin/env bash
set -euo pipefail

cd /app/src

cat > settle/settler.go <<'GO'
package settle

import (
	"fmt"
	"sort"
	"strconv"
	"strings"

	"tabsettle/model"
)

const alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"

type edge struct {
	to, rev int
	cap     int
	cost    int
}

type graph struct {
	g [][]edge
}

func newGraph(n int) *graph {
	return &graph{g: make([][]edge, n)}
}

func (gr *graph) addEdge(from, to, cap, cost int) int {
	fwd := edge{to: to, rev: len(gr.g[to]), cap: cap, cost: cost}
	rev := edge{to: from, rev: len(gr.g[from]), cap: 0, cost: -cost}
	gr.g[from] = append(gr.g[from], fwd)
	gr.g[to] = append(gr.g[to], rev)
	return len(gr.g[from]) - 1
}

func (gr *graph) minCostFlow(source, sink, need int) int {
	n := len(gr.g)
	const inf = int(^uint(0) >> 2)
	sent, total := 0, 0
	for sent < need {
		dist := make([]int, n)
		prevV := make([]int, n)
		prevE := make([]int, n)
		inQ := make([]bool, n)
		for i := range dist {
			dist[i] = inf
			prevV[i] = -1
			prevE[i] = -1
		}
		dist[source] = 0
		q := []int{source}
		inQ[source] = true
		for head := 0; head < len(q); head++ {
			v := q[head]
			inQ[v] = false
			for i, e := range gr.g[v] {
				if e.cap <= 0 {
					continue
				}
				if nd := dist[v] + e.cost; nd < dist[e.to] {
					dist[e.to] = nd
					prevV[e.to] = v
					prevE[e.to] = i
					if !inQ[e.to] {
						q = append(q, e.to)
						inQ[e.to] = true
					}
				}
			}
		}
		if prevV[sink] == -1 {
			panic("no complete settlement exists")
		}
		add := need - sent
		for v := sink; v != source; v = prevV[v] {
			if gr.g[prevV[v]][prevE[v]].cap < add {
				add = gr.g[prevV[v]][prevE[v]].cap
			}
		}
		for v := sink; v != source; v = prevV[v] {
			pv, pe := prevV[v], prevE[v]
			e := &gr.g[pv][pe]
			e.cap -= add
			gr.g[v][e.rev].cap += add
			total += add * e.cost
		}
		sent += add
	}
	return total
}

type lane struct {
	capUnits int
	cost     int
}

type tokenInfo struct {
	fromGroup string
	toGroup   string
	capUnits  int
	delta     int
}

func asciiSum(s string) int {
	total := 0
	for i := 0; i < len(s); i++ {
		total += int(s[i])
	}
	return total
}

func suffixNumber(value, prefix string) int {
	if strings.HasPrefix(value, prefix) {
		tail := value[len(prefix):]
		if tail != "" {
			if n, err := strconv.Atoi(tail); err == nil {
				return n
			}
		}
	}
	return asciiSum(value)
}

func base36(text string) (int, bool) {
	if text == "" {
		return 0, false
	}
	total := 0
	for i := 0; i < len(text); i++ {
		idx := strings.IndexByte(alphabet, strings.ToLower(text)[i])
		if idx < 0 {
			return 0, false
		}
		total = total*36 + idx
	}
	return total, true
}

func decodeGX(token string) tokenInfo {
	parts := strings.Split(token, ":")
	if len(parts) != 5 || parts[0] != "GX1" || len(parts[4]) != 1 {
		panic(fmt.Sprintf("bad GX1 token %q", token))
	}
	n, ok := base36(parts[3])
	if !ok {
		panic(fmt.Sprintf("bad GX1 payload %q", token))
	}
	check := (n*29 + asciiSum(parts[1])*3 + asciiSum(parts[2])*5) % 36
	if strings.ToLower(parts[4]) != string(alphabet[check]) {
		panic(fmt.Sprintf("bad GX1 check %q", token))
	}
	return tokenInfo{fromGroup: parts[1], toGroup: parts[2], capUnits: (n & 31) + 1, delta: ((n >> 5) & 31) - 12}
}

func decodeGL(token string) tokenInfo {
	parts := strings.Split(token, ":")
	if len(parts) != 5 || parts[0] != "GL1" || len(parts[4]) != 1 {
		panic(fmt.Sprintf("bad GL1 token %q", token))
	}
	n, ok := base36(parts[3])
	if !ok {
		panic(fmt.Sprintf("bad GL1 payload %q", token))
	}
	check := (n*37 + asciiSum(parts[1])*7 + asciiSum(parts[2])*11) % 36
	if strings.ToLower(parts[4]) != string(alphabet[check]) {
		panic(fmt.Sprintf("bad GL1 check %q", token))
	}
	return tokenInfo{fromGroup: parts[1], toGroup: parts[2], capUnits: (n & 31) + 1, delta: ((n >> 5) & 63) - 32}
}

func baseFee(d, c *account) int {
	dn := suffixNumber(d.id, "P")
	cn := suffixNumber(c.id, "P")
	fee := 10 + ((dn*17 + cn*31) % 9)
	if d.group != c.group {
		dg := suffixNumber(d.group, "team-")
		cg := suffixNumber(c.group, "team-")
		diff := dg - cg
		if diff < 0 {
			diff = -diff
		}
		fee += 7 + diff
	}
	return fee
}

func pairRebate(d, c *account) int {
	dn := suffixNumber(d.id, "P")
	cn := suffixNumber(c.id, "P")
	return 6 + ((dn*13 + cn*19 + asciiSum(d.group) + asciiSum(c.group)) % 17)
}

func lanesFor(d, c *account, rules model.Rules, gx []tokenInfo, gl []tokenInfo) []lane {
	unit := rules.SettlementUnitCents
	capUnits := rules.MaxTransferCents / unit
	cost := baseFee(d, c)
	for _, tok := range gx {
		if tok.fromGroup == d.group && tok.toGroup == c.group {
			if tok.capUnits < capUnits {
				capUnits = tok.capUnits
			}
			cost += tok.delta
		}
	}
	out := []lane{{capUnits: capUnits, cost: cost}}
	for _, tok := range gl {
		if tok.fromGroup == d.group && tok.toGroup == c.group {
			out = append(out, lane{capUnits: tok.capUnits, cost: cost + tok.delta})
		}
	}
	filtered := out[:0]
	for _, item := range out {
		if item.capUnits > 0 {
			filtered = append(filtered, item)
		}
	}
	return filtered
}

func Settle(participants []model.Participant, rules model.Rules) model.Plan {
	if rules.SettlementUnitCents <= 0 || rules.MaxTransferCents <= 0 || rules.MaxTransferCents%rules.SettlementUnitCents != 0 {
		panic("invalid settlement units")
	}
	totalBalance := 0
	for _, p := range participants {
		totalBalance += p.BalanceCents
		if p.BalanceCents%rules.SettlementUnitCents != 0 {
			panic("balance not divisible by settlement unit")
		}
	}
	if totalBalance != 0 {
		panic("ledger is not balanced")
	}

	var gx []tokenInfo
	for _, token := range rules.CorridorTokens {
		gx = append(gx, decodeGX(token))
	}
	var gl []tokenInfo
	for _, token := range rules.CorridorLaneTokens {
		gl = append(gl, decodeGL(token))
	}

	debt := debtors(participants)
	cred := creditors(participants)
	need := 0
	n := 2 + len(debt) + len(cred)
	source, sink := n-2, n-1
	gr := newGraph(n)
	for i, d := range debt {
		units := d.remaining / rules.SettlementUnitCents
		need += units
		gr.addEdge(source, i, units, 0)
	}
	for j, c := range cred {
		gr.addEdge(len(debt)+j, sink, c.remaining/rules.SettlementUnitCents, 0)
	}

	forbidden := map[string]bool{}
	for _, pair := range rules.ForbiddenPairs {
		forbidden[pair.From+"\x00"+pair.To] = true
	}

	type edgeRef struct {
		idx int
		cap int
	}
	refs := make([][][]edgeRef, len(debt))
	for i, d := range debt {
		refs[i] = make([][]edgeRef, len(cred))
		for j, c := range cred {
			if forbidden[d.id+"\x00"+c.id] {
				continue
			}
			unitCosts := []int{}
			for _, ln := range lanesFor(d, c, rules, gx, gl) {
				for k := 0; k < ln.capUnits; k++ {
					unitCosts = append(unitCosts, ln.cost)
				}
			}
			sort.Ints(unitCosts)
			if len(unitCosts) > 0 {
				unitCosts[0] -= pairRebate(d, c)
			}
			for _, cost := range unitCosts {
				edgeIdx := gr.addEdge(i, len(debt)+j, 1, cost)
				refs[i][j] = append(refs[i][j], edgeRef{idx: edgeIdx, cap: 1})
			}
		}
	}

	fee := gr.minCostFlow(source, sink, need)
	var transfers []model.Transfer
	for i, d := range debt {
		for j, c := range cred {
			usedUnits := 0
			for _, ref := range refs[i][j] {
				usedUnits += ref.cap - gr.g[i][ref.idx].cap
			}
			if usedUnits > 0 {
				transfers = append(transfers, model.Transfer{
					From:        d.id,
					To:          c.id,
					AmountCents: usedUnits * rules.SettlementUnitCents,
				})
			}
		}
	}
	sort.Slice(transfers, func(i, j int) bool {
		if transfers[i].From != transfers[j].From {
			return transfers[i].From < transfers[j].From
		}
		if transfers[i].To != transfers[j].To {
			return transfers[i].To < transfers[j].To
		}
		return transfers[i].AmountCents < transfers[j].AmountCents
	})
	return model.Plan{SettlementFeeUnits: fee, Transfers: transfers}
}
GO

cat > settle/validate.go <<'GO'
package settle

import (
	"fmt"

	"tabsettle/model"
)

func Validate(participants []model.Participant, rules model.Rules, plan model.Plan) error {
	bal := make(map[string]int, len(participants))
	for _, p := range participants {
		bal[p.ID] = p.BalanceCents
	}
	sent := map[string]int{}
	recv := map[string]int{}
	for _, t := range plan.Transfers {
		bf, okf := bal[t.From]
		bt, okt := bal[t.To]
		if !okf || !okt {
			return fmt.Errorf("transfer references unknown participant")
		}
		if t.From == t.To || t.AmountCents <= 0 || t.AmountCents%rules.SettlementUnitCents != 0 {
			return fmt.Errorf("invalid transfer")
		}
		if bf >= 0 || bt <= 0 {
			return fmt.Errorf("wrong transfer direction")
		}
		sent[t.From] += t.AmountCents
		recv[t.To] += t.AmountCents
	}
	for _, p := range participants {
		if p.BalanceCents < 0 && sent[p.ID] != -p.BalanceCents {
			return fmt.Errorf("debtor %s not settled exactly", p.ID)
		}
		if p.BalanceCents > 0 && recv[p.ID] != p.BalanceCents {
			return fmt.Errorf("creditor %s not settled exactly", p.ID)
		}
	}
	return nil
}
GO

cat > main.go <<'GO'
package main

import (
	"fmt"
	"os"

	"tabsettle/cli"
	"tabsettle/loader"
	"tabsettle/report"
	"tabsettle/settle"
)

func main() {
	args, err := cli.Parse(os.Args[1:])
	if err != nil {
		fmt.Fprintln(os.Stderr, "argument error:", err)
		os.Exit(2)
	}
	participants, err := loader.ReadParticipants(args.Participants)
	if err != nil {
		fmt.Fprintln(os.Stderr, "failed to read participants:", err)
		os.Exit(1)
	}
	rules, err := loader.ReadRules(args.Rules)
	if err != nil {
		fmt.Fprintln(os.Stderr, "failed to read rules:", err)
		os.Exit(1)
	}
	plan := settle.Settle(participants, rules)
	if err := settle.Validate(participants, rules, plan); err != nil {
		fmt.Fprintln(os.Stderr, "invalid plan:", err)
		os.Exit(1)
	}
	if err := loader.WritePlan(args.Out, plan); err != nil {
		fmt.Fprintln(os.Stderr, "failed to write plan:", err)
		os.Exit(1)
	}
	report.Print(os.Stderr, report.Summarize(participants, plan))
	fmt.Printf("wrote %d transfers for %d participants to %s\n", len(plan.Transfers), len(participants), args.Out)
}
GO

gofmt -w main.go settle/settler.go settle/validate.go
go run . -participants /app/input/participants.json -rules /app/input/rules.json -out /app/output/plan.json
