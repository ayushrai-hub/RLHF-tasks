package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

// CLI driver. DO NOT MODIFY this file. Reads one case per line
// ("<case-id> <seq-json>"), applies Optimize to each sequence, and prints
// "<case-id> <optimized-seq-json>", one line per case.
func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: litpre <cases-file>")
		os.Exit(2)
	}
	f, err := os.Open(os.Args[1])
	if err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(2)
	}
	defer f.Close()
	out := bufio.NewWriter(os.Stdout)
	defer out.Flush()
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1<<20), 1<<24)
	for sc.Scan() {
		line := strings.TrimRight(sc.Text(), "\r\n")
		if strings.TrimSpace(line) == "" {
			continue
		}
		id, spec, found := strings.Cut(line, " ")
		if !found {
			fmt.Fprintln(os.Stderr, "error: malformed case line:", line)
			os.Exit(2)
		}
		seq, err := ParseSeq(spec)
		if err != nil {
			fmt.Fprintln(os.Stderr, "error:", err)
			os.Exit(2)
		}
		seq.Optimize()
		fmt.Fprintf(out, "%s %s\n", id, DumpSeq(&seq))
	}
	if err := sc.Err(); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(2)
	}
}
