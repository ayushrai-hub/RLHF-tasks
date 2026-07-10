package app

import (
	"errors"

	"breach-ledger/internal/correlate"
	"breach-ledger/internal/model"
	"breach-ledger/internal/parse"
	"breach-ledger/internal/report"
)

func Run(bundle string, output string) error {
	ev, issues := parse.P0(bundle)
	if picked := model.ME0(issues); picked != nil {
		_ = report.R0(output, *picked)
		return errors.New(picked.Code)
	}
	ev = correlate.Analyze(ev)
	timeline := correlate.C1(ev)
	if err := report.R1(output, ev); err != nil {
		return err
	}
	if err := report.R2(output, timeline); err != nil {
		return err
	}
	if err := report.R3(output, ev.IOCs); err != nil {
		return err
	}
	return report.R4(output, ev)
}
