package cli

import (
	"fmt"

	"localauthz/internal/drive"
	"localauthz/internal/report"
)

func Execute(args []string) error {
	if len(args) == 0 {
		return fmt.Errorf(usage())
	}
	switch args[0] {
	case "run-case":
		opts, err := parseRunCase(args[1:])
		if err != nil {
			return err
		}
		runner, err := drive.NewRunner(opts.CasePath, opts.StatePath, opts.Resume, opts.StopAfterStep)
		if err != nil {
			return err
		}
		trace, err := runner.Run()
		if err != nil {
			return err
		}
		return report.WriteTrace(opts.OutPath, trace)
	default:
		return unknownCommand(args[0])
	}
}
