# Split DNS route leak

Per-link domain search on the local Ruby resolver lab under `/app/environment` is leaking internal name classes onto external link surfaces after link changes, VPN race reorderings, and negative-cache carryover. Public matrix arms (`run_a`, `run_b`) can finish with healthy interim row tallies in `/app/environment/fixtures/q9/p9_stub.json` while held-out arms still disagree on graded bytes.

Repair Ruby sources under `/app/environment` (not output-only edits) so the normal build and checker pipeline regenerates `/app/output/route_audit.json`. Static JSON, profile-only blocklists, or test edits are not sufficient.

## Build and checker

```bash
/app/environment/scripts/build_all.sh
ruby /app/environment/cmd/var_check/main.rb --matrix-full --out /app/output/route_audit.json
```

The matrix checker at `ruby /app/environment/cmd/var_check/main.rb` (var_check) drives all profile arms, computes per-row `route_fingerprint` digests, and must exit 0 when every arm converges. Success requires public arms `run_a` and `run_b` and held-out arms `run_c` (VPN-race reorder) and `run_d` (duplicated recovery passes) to complete cleanly.

## Contract

Read `/app/environment/docs/pact_r4.md` for digest reduction over per-run slice files under `/app/environment/var/state/`, numeric band class tokens, recovery command, and cross-path invariants. Read `/app/environment/docs/slice_layout.md` for binary slice layout. Partial log tails live under `/app/environment/fixtures/logs/`; authoritative bytes live under `/app/environment/fixtures/blk/`.

`/app/output/route_audit.json` follows pact_r4.md. The top-level matrix_runs array holds one record per profile arm and path kind.

Each record includes profile_key naming the arm. The path_kind field distinguishes uninterrupted versus recovered execution. The route_fingerprint field stores a 64-character lowercase hex digest of rebuilt slice bytes. The band_class field reports the effective downgrade band as an integer. The internal_leak_count field counts internal query-class rows on external link surfaces. The cross_path_match field reports whether uninterrupted and recovered digests agree for the profile.

Terminal convergence requires matching digests across path kinds for every profile arm, including held-out reorder and duplicate-recovery cases.

Recovery after scratch reset uses only the command documented in pact_r4.md (via `/app/environment/migrations/mig9.sh` and `/app/environment/fixtures/seed/arena_seed.bin`) and must preserve lane epoch anchors at `/app/environment/var/anchor/lane.epoch`.

Interim rows in the q9 stub (`interim_rows` array) are smoke-only display objects; terminal grading binds JSON output to rebuilt slice bytes.

## Verifier

Tests rebuild from sources, run the matrix checker, and validate the pact_r4 contract.
