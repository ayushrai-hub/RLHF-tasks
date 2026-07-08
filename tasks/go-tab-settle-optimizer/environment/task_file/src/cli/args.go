package cli

import "flag"

// Args holds the resolved command-line configuration.
type Args struct {
	Participants string
	Rules        string
	Out          string
}

// Parse reads the -participants, -rules and -out flags, defaulting to the
// standard input/output locations used by the task.
func Parse(argv []string) (Args, error) {
	fs := flag.NewFlagSet("tabsettle", flag.ContinueOnError)
	fs.Usage = func() { usage(fs.Output()) }

	var a Args
	fs.StringVar(&a.Participants, "participants", defaultParticipants, "path to participants JSON")
	fs.StringVar(&a.Rules, "rules", defaultRules, "path to rules JSON")
	fs.StringVar(&a.Out, "out", defaultOut, "path to write the settlement plan")

	if err := fs.Parse(argv); err != nil {
		return Args{}, err
	}
	return a, nil
}
