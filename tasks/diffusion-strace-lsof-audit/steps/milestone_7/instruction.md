`relay_lane.md` still fails audit after the edge-case parser work. Repair that runbook so fenced excerpts stay offline and under the configured run directory, then rebuild and run the verify pass per `/app/docs/verification_contract.md` and `/app/data/scenario_manifest.json`.

Required relay-lane repairs:
- Remove every `connect(` line from fenced `strace` excerpts.
- Remove every `/etc/diffusion` path from fenced `strace` and `lsof` excerpts; keep relay state under `/var/lib/diffusion-runs/current` instead.
- Drop remote TCP rows from fenced `lsof` excerpts.

Rebuild with `bash /app/scripts/build_all.sh`, then run `bash /app/scripts/milestone_probes.sh verify`. The probe must write `/app/output/verification_report.json` with `schema_tag` `tb3-kdiff-trace-04`, `manifest_version` `2024.06`, `bundles_scanned` `7`, `trace_blocks_harvested` `15`, and `audit_clean`, `relay_lane_offline`, `manifest_sources_match`, and `manifest_blocks_match` all true.

Signal completion once the verify probe passes.
