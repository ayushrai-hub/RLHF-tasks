# Verification contract

`verification_report.json` uses `schema_tag` `tb3-kdiff-trace-04`.

The verify pass cross-checks repaired runbooks against `/app/data/scenario_manifest.json` after a clean audit.

| field | type | meaning |
|-------|------|---------|
| manifest_version | string | Echo of `manifest_version` from the scenario manifest |
| bundles_scanned | int | Markdown runbooks under the manifest `bundle_root` |
| trace_blocks_harvested | int | Total fenced trace excerpts harvested |
| audit_clean | bool | True when the audit pass reports zero open violations |
| relay_lane_offline | bool | True when `relay_lane.md` contains no remote `connect(` lines and no `/etc/diffusion` paths in fenced excerpts |

After milestone cleanup, `audit_clean` and `relay_lane_offline` must both be true.
