# Audit contract

`policy_audit.json` uses `schema_tag` `tb3-kdiff-trace-02`.

Schema fields:
- `violation_count` means the number of open policy violations after deduplication.
- `violation_kinds` means the distinct policy kind strings among the four kinds below.
- `run_dir` means the active run directory from `/app/policy/workflow_policy.toml`.
- `socket_rows` means reconstructed non-loopback `host:port` peers from strace `connect` lines per `/app/docs/strace_contract.md`.
- `violations[].detail` means the detail payload for a finding. For `write_outside_run_dir`, use the bare absolute path outside `run_dir` (for example `/etc/diffusion/cache/state.bin`), not a descriptive sentence.

| field | type | meaning |
|-------|------|---------|
| violation_count | int | Open policy violations after deduplication |
| violation_kinds | string[] | Distinct kinds among `rng_unseeded`, `write_outside_run_dir`, `descriptor_leak`, `network_egress` |
| run_dir | string | Active run directory from `/app/policy/workflow_policy.toml` |
| socket_rows | string[] | Non-loopback `host:port` peers from strace `connect` lines |
| violations[].kind | string | Policy kind |
| violations[].source | string | Runbook relative path |
| violations[].detail | string | Kind-specific detail; `write_outside_run_dir` uses the bare offending path |

Violation accounting:

- Collapse duplicate findings that share the same `(kind, source, detail)` triple before computing `violation_count`.
- The same absolute path reported from both strace and lsof in one runbook counts once when the triple matches.

Violation kinds:

- `rng_unseeded` means a documented shell invoke under `<!-- shell-invoke -->` launches `diffusion-sample` without `--seed`.
- `write_outside_run_dir` means a strace or lsof path targets a location outside `run_dir`.
- `descriptor_leak` means paired `lsof` snapshots in the same runbook show `fd_delta` strictly greater than `fd_leak_threshold` per `/app/docs/lsof_contract.md`.
- `network_egress` means strace records `connect` to a non-loopback peer or the shell invoke references remote HTTP.

Against the current runbooks the audit pass must surface nine violations spanning all four kinds before runbook cleanup.
