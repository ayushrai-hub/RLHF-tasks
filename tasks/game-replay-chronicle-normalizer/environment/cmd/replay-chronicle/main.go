package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/terminus/game-replay-chronicle-normalizer/internal/chronicle"
	"github.com/terminus/game-replay-chronicle-normalizer/internal/merge"
	"github.com/terminus/game-replay-chronicle-normalizer/internal/validate"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: replay-chronicle <normalize|validate> ...")
		os.Exit(2)
	}
	switch os.Args[1] {
	case "normalize":
		os.Exit(runNormalize(os.Args[2:]))
	case "validate":
		os.Exit(runValidate(os.Args[2:]))
	default:
		fmt.Fprintln(os.Stderr, "unknown subcommand")
		os.Exit(2)
	}
}

func runNormalize(args []string) int {
	fs := flag.NewFlagSet("normalize", flag.ExitOnError)
	inputDir := fs.String("input-dir", "", "directory of .grsh shards")
	output := fs.String("output", "", "output chronicle JSON path")
	_ = fs.Parse(args)

	dir := *inputDir
	if root := os.Getenv("TB3_FIXTURE_ROOT"); root != "" {
		dir = root
	}
	if dir == "" || *output == "" {
		fmt.Fprintln(os.Stderr, "input-dir and output required")
		return 2
	}
	shards, events, err := merge.NormalizeDir(dir)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	ch, err := chronicle.Build(shards, events)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	if err := chronicle.WriteJSON(*output, ch); err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	return 0
}

func runValidate(args []string) int {
	fs := flag.NewFlagSet("validate", flag.ExitOnError)
	input := fs.String("input", "", "chronicle JSON path")
	_ = fs.Parse(args)

	path := *input
	if root := os.Getenv("TB3_FIXTURE_ROOT"); root != "" {
		path = root
	}
	if path == "" {
		fmt.Fprintln(os.Stderr, "input required")
		return 2
	}
	ch, err := chronicle.LoadJSON(path)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	if !validate.MatchesIntegrity(ch.Events, ch.Integrity) {
		fmt.Fprintln(os.Stderr, "integrity mismatch")
		return 1
	}
	return 0
}
