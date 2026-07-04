package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"ckptplan/internal/model"
	"ckptplan/internal/plan"
)

// ckptplan is an activation-checkpointing planner for a sequential neural
// network. The ordered layers are split into contiguous segments; the first
// layer of each segment is a retained checkpoint whose activation stays
// resident, and the remaining layers of the segment are recomputed during the
// backward pass.
//
// Subcommand:
//
//	ckptplan plan --budget B
//	    Reads the layer list from stdin (one layer per line, two non-negative
//	    integers "<activation_mem> <recompute_cost>") and prints the chosen plan
//	    as a single JSON object:
//	        {"n_segments":N,"boundaries":[...],"est_peak_mem":P,
//	         "est_recompute":R,"total_activation":T,"feasible":BOOL}
func main() {
	if len(os.Args) < 2 {
		usage()
	}
	switch os.Args[1] {
	case "plan":
		cmdPlan(os.Args[2:])
	default:
		usage()
	}
}

func usage() {
	fmt.Fprintln(os.Stderr, "usage: ckptplan plan --budget B < layers")
	os.Exit(2)
}

func cmdPlan(args []string) {
	budget := 0
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--budget":
			if i+1 >= len(args) {
				fmt.Fprintln(os.Stderr, "missing value for --budget")
				os.Exit(2)
			}
			v, err := strconv.Atoi(args[i+1])
			if err != nil || v < 1 {
				fmt.Fprintln(os.Stderr, "invalid --budget")
				os.Exit(2)
			}
			budget = v
			i++
		default:
			fmt.Fprintf(os.Stderr, "unknown argument %q\n", args[i])
			os.Exit(2)
		}
	}
	if budget == 0 {
		fmt.Fprintln(os.Stderr, "missing --budget")
		os.Exit(2)
	}

	layers, err := model.Parse(os.Stdin)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	p := plan.Build(layers, budget)

	var b strings.Builder
	b.WriteString("{")
	fmt.Fprintf(&b, "\"n_segments\":%d,", p.NSegments)
	b.WriteString("\"boundaries\":[")
	for i, v := range p.Boundaries {
		if i > 0 {
			b.WriteString(",")
		}
		fmt.Fprintf(&b, "%d", v)
	}
	b.WriteString("],")
	fmt.Fprintf(&b, "\"est_peak_mem\":%d,", p.EstPeakMem)
	fmt.Fprintf(&b, "\"est_recompute\":%d,", p.EstRecompute)
	fmt.Fprintf(&b, "\"total_activation\":%d,", p.TotalActivation)
	fmt.Fprintf(&b, "\"feasible\":%t", p.Feasible)
	b.WriteString("}")
	fmt.Println(b.String())
}
