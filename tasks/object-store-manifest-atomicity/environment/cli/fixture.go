package app

import (
	"flag"
	"fmt"
	"io"

	"terminal.local/objectmanifest/internal/store"
)

func runFixture(args []string, stdout io.Writer, stderr io.Writer) int {
	fs := flag.NewFlagSet("fixture", flag.ContinueOnError)
	fs.SetOutput(stderr)
	scenario := ""
	root := ""
	fs.StringVar(&scenario, "scenario", "", "fixture scenario")
	fs.StringVar(&root, "store", "", "store root")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	if scenario == "" || root == "" {
		fmt.Fprintln(stderr, "--scenario and --store are required")
		return 2
	}
	if err := store.WriteScenario(root, scenario); err != nil {
		fmt.Fprintf(stderr, "fixture: %v\n", err)
		return 1
	}
	fmt.Fprintf(stdout, "created %s at %s\n", scenario, root)
	return 0
}
