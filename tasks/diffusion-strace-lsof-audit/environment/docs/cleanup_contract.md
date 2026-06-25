# Cleanup contract

`cleanup_report.json` uses `schema_tag` `tb3-kdiff-trace-03`.

Schema fields:
- `open_violations` means the remaining violation count after runbook repairs.
- `policy_pass_count` means how many of the four policy kinds have zero open findings (max 4).
- `runbook_sha256` means the lowercase hex SHA-256 over concatenated runbook bytes in sorted path order.

| field | type | meaning |
|-------|------|---------|
| open_violations | int | Remaining violations after runbook repairs |
| policy_pass_count | int | Count of the four policy kinds with zero open findings (max 4) |
| runbook_sha256 | string | Lowercase hex SHA-256 over concatenated runbook bytes in sorted path order |

After runbook cleanup and a rebuild, `open_violations` must be zero and `policy_pass_count` must be four.

Per-runbook content repairs (paths relative to `/app/docs/q3_bundles/`):

| runbook | required change |
|---------|-----------------|
| `replay_lane.md` | shell-invoke must include `--seed` on `diffusion-sample` |
| `mirror_lane.md` | no `curl` or `connect(` anywhere in the file |
| `cache_spill.md` | no `/etc/diffusion` or `/var/tmp/diffusion` paths in fenced excerpts |
| `burst_lane.md` | no `/tmp/diffusion-run` paths in fenced excerpts |
