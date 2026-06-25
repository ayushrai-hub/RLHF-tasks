Several runbooks under `/app/docs/q3_bundles/` still fail policy audit even though the parsers now work. Edit the runbook prose and embedded excerpts so each failing bundle complies with the workflow policy in `/app/policy/workflow_policy.toml`, then rebuild and re-audit until cleanup passes.

Repair these four runbooks before the cleanup probe:
- `replay_lane.md`: document a seeded `diffusion-sample` launch — the `<!-- shell-invoke -->` line must include `--seed` and the runbook file must contain that flag.
- `mirror_lane.md`: stop documenting remote pulls — shell-invoke, fenced `strace`, and fenced `lsof` must not contain `curl` or `connect(` anywhere in the file.
- `cache_spill.md`: keep state under the run directory — fenced `strace` and `lsof` must not reference `/etc/diffusion` or `/var/tmp/diffusion`.
- `burst_lane.md`: keep paired `lsof` snapshots flat — fenced excerpts must not reference `/tmp/diffusion-run`; scratch paths must stay under the configured run directory instead.

Rebuild with `bash /app/scripts/build_all.sh`, then run `bash /app/scripts/milestone_probes.sh clean`. The probe must write `/app/output/cleanup_report.json` with `schema_tag` `tb3-kdiff-trace-03`, `open_violations` `0`, `policy_pass_count` `4`, and `runbook_sha256` per `/app/docs/cleanup_contract.md`.

Signal completion once the cleanup probe passes.
