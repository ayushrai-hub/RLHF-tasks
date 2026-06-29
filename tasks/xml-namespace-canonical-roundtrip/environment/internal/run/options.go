package run

import "fmt"

type BuildOptions struct {
	Input string
	Out   string
}

type ValidateOptions struct {
	Input    string
	Artifact string
}

type ReplayOptions struct {
	Input    string
	Artifact string
}

type BatchOptions struct {
	List string
	Out  string
}

func Require(value, label string) error {
	if value == "" {
		return fmt.Errorf("missing required %s", label)
	}
	return nil
}
