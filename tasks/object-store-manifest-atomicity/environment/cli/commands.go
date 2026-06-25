package app

import (
	"fmt"
	"io"
)

type commandFunc func([]string, io.Writer, io.Writer) int

type command struct {
	name string
	run  commandFunc
	note string
}

var commands = []command{
	{name: "fixture", run: runFixture, note: "create a deterministic local store"},
	{name: "rebuild", run: runRebuild, note: "regenerate manifest, checksum report, and provenance"},
	{name: "smoke", run: runSmoke, note: "verify manifest paths can be opened"},
	{name: "doctor", run: runDoctor, note: "print receipt and object summary"},
}

func Run(args []string, stdout io.Writer, stderr io.Writer) int {
	if len(args) == 0 || args[0] == "help" || args[0] == "--help" || args[0] == "-h" {
		printHelp(stdout)
		return 0
	}
	for _, c := range commands {
		if args[0] == c.name {
			return c.run(args[1:], stdout, stderr)
		}
	}
	fmt.Fprintf(stderr, "unknown command %q\n", args[0])
	printHelp(stderr)
	return 2
}

func printHelp(w io.Writer) {
	fmt.Fprintln(w, "ostore local manifest utility")
	fmt.Fprintln(w, "")
	fmt.Fprintln(w, "commands:")
	for _, c := range commands {
		fmt.Fprintf(w, "  %-8s %s\n", c.name, c.note)
	}
}
