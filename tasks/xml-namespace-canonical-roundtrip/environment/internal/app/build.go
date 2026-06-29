package app

import (
	"fmt"

	"nsx/internal/check"
	"nsx/internal/emit"
	"nsx/internal/load"
	"nsx/internal/pass"
	"nsx/internal/report"
	"nsx/internal/run"
)

func Build(opts run.BuildOptions) error {
	if err := run.Require(opts.Input, "--input"); err != nil {
		return err
	}
	if err := run.Require(opts.Out, "--out"); err != nil {
		return err
	}
	if err := report.PrepareOutput(opts.Out); err != nil {
		return err
	}
	audit := report.NewAudit(opts.Input, opts.Out)
	doc, err := load.ReadFile(opts.Input)
	if err != nil {
		audit.Add("parse", "error")
		_ = report.WriteAudit(opts.Out, audit)
		return err
	}
	audit.Add("parse", "ok")
	pass.Apply(doc)
	audit.Add("normalize", "ok")
	canonical, err := emit.Render(doc)
	if err != nil {
		return err
	}
	if err := report.WriteCanonical(opts.Out, canonical); err != nil {
		return err
	}
	audit.Add("serialize", "ok")
	if err := check.Document(doc); err != nil {
		audit.Add("validate", "error")
		_ = report.WriteAudit(opts.Out, audit)
		return fmt.Errorf("validation failed: %w", err)
	}
	if err := report.WriteScope(opts.Out, doc); err != nil {
		return err
	}
	audit.Add("validate", "ok")
	if err := report.WriteAudit(opts.Out, audit); err != nil {
		return err
	}
	return report.WriteInputMarker(opts.Out, opts.Input)
}
