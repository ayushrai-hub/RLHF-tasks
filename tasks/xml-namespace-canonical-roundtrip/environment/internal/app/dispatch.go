package app

import (
	"flag"
	"fmt"

	"nsx/internal/run"
)

func Dispatch(args []string) error {
	if len(args) == 0 {
		return fmt.Errorf("usage: nsx <build|validate|replay|batch> [flags]")
	}
	switch args[0] {
	case "build":
		fs := flag.NewFlagSet("build", flag.ContinueOnError)
		var opts run.BuildOptions
		fs.StringVar(&opts.Input, "input", "", "input XML file")
		fs.StringVar(&opts.Out, "out", "", "output directory")
		if err := fs.Parse(args[1:]); err != nil {
			return err
		}
		return Build(opts)
	case "validate":
		fs := flag.NewFlagSet("validate", flag.ContinueOnError)
		var opts run.ValidateOptions
		fs.StringVar(&opts.Input, "input", "", "input XML file")
		fs.StringVar(&opts.Artifact, "artifact", "", "artifact directory")
		if err := fs.Parse(args[1:]); err != nil {
			return err
		}
		return Validate(opts)
	case "replay":
		fs := flag.NewFlagSet("replay", flag.ContinueOnError)
		var opts run.ReplayOptions
		fs.StringVar(&opts.Input, "input", "", "input XML file")
		fs.StringVar(&opts.Artifact, "artifact", "", "artifact directory")
		if err := fs.Parse(args[1:]); err != nil {
			return err
		}
		return Replay(opts)
	case "batch":
		fs := flag.NewFlagSet("batch", flag.ContinueOnError)
		var opts run.BatchOptions
		fs.StringVar(&opts.List, "list", "", "batch list file")
		fs.StringVar(&opts.Out, "out", "", "batch output directory")
		if err := fs.Parse(args[1:]); err != nil {
			return err
		}
		return Batch(opts)
	default:
		return fmt.Errorf("unknown command %q", args[0])
	}
}
