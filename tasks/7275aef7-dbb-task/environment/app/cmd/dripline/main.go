package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	input := flag.String("input", "/app/input", "input directory")
	output := flag.String("output", "/app/output/dripline_report.json", "output report path")
	flag.Parse()

	_ = input
	_ = output
	fmt.Fprintln(os.Stderr, "dripline auditor is not implemented yet")
	os.Exit(1)
}
