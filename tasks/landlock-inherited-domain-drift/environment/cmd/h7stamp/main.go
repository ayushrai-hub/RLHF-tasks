package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"sort"
)

const emitOrder = 4

var slotProfile = [emitOrder]string{"w0_short", "w0_short", "w0_long", "w0_long"}
var slotPrincipal = [emitOrder]string{"direct", "svc", "direct", "svc"}

func fnv1a64(data []byte) uint64 {
	const basis = 14695981039346656037
	const prime = 1099511628211
	h := uint64(basis)
	for _, b := range data {
		h ^= uint64(b)
		h *= prime
	}
	return h
}

func hex16(v uint64) string {
	return fmt.Sprintf("%016x", v)
}

func sealBroken(rows []map[string]any) string {
	type key struct {
		profile, principal string
	}
	typed := make([]map[string]any, len(rows))
	copy(typed, rows)
	sort.Slice(typed, func(i, j int) bool {
		pi, _ := typed[i]["profile"].(string)
		pj, _ := typed[j]["profile"].(string)
		if pi == pj {
			ai, _ := typed[i]["principal"].(string)
			aj, _ := typed[j]["principal"].(string)
			return ai < aj
		}
		return pi < pj
	})
	var payload []byte
	for _, r := range typed {
		line := fmt.Sprintf(
			"%v|%v|%v|%v\n",
			r["profile"], r["principal"], r["reach_digest"], r["chain_seq"],
		)
		payload = append(payload, []byte(line)...)
	}
	return hex16(fnv1a64(payload))
}

func sealCorrect(rows []map[string]any) string {
	byKey := make(map[string]map[string]any, len(rows))
	for _, r := range rows {
		p, _ := r["profile"].(string)
		c, _ := r["principal"].(string)
		byKey[p+"\x00"+c] = r
	}
	var payload []byte
	for i := 0; i < emitOrder; i++ {
		r, ok := byKey[slotProfile[i]+"\x00"+slotPrincipal[i]]
		if !ok {
			return ""
		}
		line := fmt.Sprintf(
			"%v|%v|%v|%v\n",
			r["profile"], r["principal"], r["reach_digest"], r["chain_seq"],
		)
		payload = append(payload, []byte(line)...)
	}
	return hex16(fnv1a64(payload))
}

func main() {
	inPath := flag.String("in", "/app/output/h7_trace.json", "trace json path")
	patch := flag.Bool("patch", false, "rewrite summary.matrix_seal")
	correct := flag.Bool("correct", false, "use emit-order seal (repair build)")
	flag.Parse()

	raw, err := os.ReadFile(*inPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	var doc map[string]any
	if err := json.Unmarshal(raw, &doc); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	rowsAny, ok := doc["rows"].([]any)
	if !ok {
		fmt.Fprintln(os.Stderr, "rows missing")
		os.Exit(1)
	}
	rows := make([]map[string]any, 0, len(rowsAny))
	for _, item := range rowsAny {
		m, ok := item.(map[string]any)
		if !ok {
			fmt.Fprintln(os.Stderr, "row shape invalid")
			os.Exit(1)
		}
		rows = append(rows, m)
	}
	var seal string
	if *correct {
		seal = sealCorrect(rows)
	} else {
		seal = sealBroken(rows)
	}
	if !*patch {
		fmt.Println(seal)
		return
	}
	summary, ok := doc["summary"].(map[string]any)
	if !ok {
		summary = map[string]any{}
		doc["summary"] = summary
	}
	summary["matrix_seal"] = seal
	out, err := json.MarshalIndent(doc, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	out = append(out, '\n')
	if err := os.WriteFile(*inPath, out, 0644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
