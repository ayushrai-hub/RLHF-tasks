A batch stats tool under `/app/environment` matches reference output on fresh full runs, but continued runs diverge on second-moment metrics, tail quantiles, and cross-branch totals even though per-branch health digests still agree. The tool uses fixed seeds and deterministic inputs.

Fix source under `/app/environment` so the normal pipeline regenerates outputs. Static writes to `/app/output/`, wrapper-only edits, test changes, clearing every reuse slot on each continue, or widening numeric fields only at report emission are not enough.

After editing sources, rebuild with `/app/environment/scripts/build_stats.sh` before using `/usr/local/bin/stream-stats`. The verifier calls that installed path and does not rebuild for you.

Commands, seed fixtures, tolerance bands, reservoir sizing, generation fields, fence journal, and trace ordering live in `/app/environment/docs/operator_notes.md`. Regenerated artifacts: `/app/output/run_report.json`, `/app/output/merge_trace.jsonl`, `/app/output/resume_diff_summary.json`.

The run report includes profile, global_total, branch_totals, observed_merge_steps, frame_gen, and plan_digest. Trace rows include step, left_branch, right_branch, and combine_rank. Resume diff includes metric_deltas, ordering_violations, max_combine_rank, frame_gen, seal_gen, drain_wm, and plan_digest.

Cold and continued runs for the same seed should agree within the documented bands on published metrics, branch totals, plan digest, merge-trace pairs and combine_rank order, and generation fields across the run report, resume diff, reuse state, fence journal, and WAL seal peak. A second continue with no new events should leave metrics and plan digest unchanged. Interleaved seeds, WAL salvage after malformed lines, and foreign-generation WAL rows are part of normal operator workflows and should not leave stale plan, generation, or partial-sum state behind.
