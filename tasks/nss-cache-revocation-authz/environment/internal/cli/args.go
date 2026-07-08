package cli

import (
	"errors"
	"flag"
	"fmt"
)

type RunCaseOptions struct {
	CasePath      string
	StatePath     string
	OutPath       string
	Resume        bool
	StopAfterStep int
}

func parseRunCase(args []string) (RunCaseOptions, error) {
	fs := flag.NewFlagSet("run-case", flag.ContinueOnError)
	var opts RunCaseOptions
	fs.StringVar(&opts.CasePath, "case", "", "scenario JSON path")
	fs.StringVar(&opts.StatePath, "state", "", "state directory path")
	fs.StringVar(&opts.OutPath, "out", "", "authorization trace output path")
	fs.BoolVar(&opts.Resume, "resume", false, "continue from persisted run manifest and cache state")
	stopAfter := fs.Int("stop-after-step", 0, "execute only through this 1-based step number")
	if err := fs.Parse(args); err != nil {
		return opts, err
	}
	opts.StopAfterStep = *stopAfter
	if opts.CasePath == "" || opts.StatePath == "" || opts.OutPath == "" {
		return opts, errors.New("run-case requires --case, --state, and --out")
	}
	return opts, nil
}

func usage() string {
	return "usage: authzctl run-case --case <scenario.json> --state <state-dir> --out <trace.json> [--resume] [--stop-after-step N]"
}

func unknownCommand(name string) error {
	return fmt.Errorf("unknown command %q\n%s", name, usage())
}
