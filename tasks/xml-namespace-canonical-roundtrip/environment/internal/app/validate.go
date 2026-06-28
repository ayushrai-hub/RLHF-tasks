package app

import (
	"bytes"
	"fmt"
	"os"

	"nsx/internal/check"
	"nsx/internal/emit"
	"nsx/internal/load"
	"nsx/internal/pass"
	"nsx/internal/run"
)

func Validate(opts run.ValidateOptions) error {
	if err := run.Require(opts.Input, "--input"); err != nil {
		return err
	}
	if err := run.Require(opts.Artifact, "--artifact"); err != nil {
		return err
	}
	doc, err := load.ReadFile(opts.Input)
	if err != nil {
		return err
	}
	pass.Apply(doc)
	if err := check.Document(doc); err != nil {
		return err
	}
	want, err := emit.Render(doc)
	if err != nil {
		return err
	}
	got, err := os.ReadFile(run.CanonicalPath(opts.Artifact))
	if err != nil {
		return err
	}
	if !bytes.Equal(got, []byte(want)) {
		return fmt.Errorf("canonical artifact does not match regenerated form")
	}
	if err := check.ScopeDocument(doc, opts.Artifact); err != nil {
		return err
	}
	return check.Artifacts(opts.Artifact)
}

func Replay(opts run.ReplayOptions) error {
	if err := Validate(run.ValidateOptions{Input: opts.Input, Artifact: opts.Artifact}); err != nil {
		return err
	}
	return check.InputMarker(opts.Artifact, opts.Input)
}
