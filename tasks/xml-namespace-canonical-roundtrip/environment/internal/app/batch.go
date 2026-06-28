package app

import (
	"fmt"

	"nsx/internal/report"
	"nsx/internal/run"
)

func Batch(opts run.BatchOptions) error {
	if err := run.Require(opts.List, "--list"); err != nil {
		return err
	}
	if err := run.Require(opts.Out, "--out"); err != nil {
		return err
	}
	inputs, err := report.ReadBatchList(opts.List)
	if err != nil {
		return err
	}
	if len(inputs) == 0 {
		return fmt.Errorf("empty batch list")
	}
	members := make([]string, 0, len(inputs))
	for _, input := range inputs {
		members = append(members, report.MemberDir(opts.Out, input))
	}
	if err := report.PrepareBatchOutput(opts.Out, members); err != nil {
		return err
	}
	rows := make([]report.BatchRow, 0, len(inputs))
	for _, input := range inputs {
		member := report.MemberDir(opts.Out, input)
		if err := Build(run.BuildOptions{Input: input, Out: member}); err != nil {
			return err
		}
		digest, err := report.CanonicalSHA256(member)
		if err != nil {
			return err
		}
		rows = append(rows, report.BatchRow{
			Input:           input,
			ArtifactDir:     member,
			CanonicalSHA256: digest,
		})
	}
	return report.WriteBatchLedger(opts.Out, rows)
}
