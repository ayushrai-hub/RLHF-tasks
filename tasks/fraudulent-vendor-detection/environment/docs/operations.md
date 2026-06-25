# Operations

## Go packages to inspect

| Package / path | Role |
|----------------|------|
| `internal/ingest` | Period scheduler, invoice binding, period snapshots |
| `internal/sim` | Panel fixtures and vendor spend caps |
| `vm` | Exposure visibility for committed vs pending weight points |
| `blob` | Vendor-cap reservation while attributing an invoice row |
| `batch` | Period-end settlement of pending exposure weights |
| `internal/decoy` | Infrastructure SLO and payment_terms-rate helpers (misleading greens) |
| `internal/io` | JSON report writer |
| `cmd/vendorlab` | CLI entry |

Supporting docs: `report_schema.md`, `fixture_layout.md`.

## Bundled profiles

Profiles under `/app/environment/profiles/`:

| Profile | Panel | View | Notes |
|---------|-------|------|-------|
| `steady.json` | north | line_item | baseline control |
| `burst.json` | north | vendor_graph | primary regression |
| `relay.json` | north | vendor_graph | alternate seed |
| `solo_stream.json` | north | vendor_graph | single-stage geometry |
| `mixed_fleet.json` | south | vendor_graph | second corpus |
| `delay_ticks.json` | north | vendor_graph | extended period window |
| `south_relay.json` | south | vendor_graph | alternate south seed |
| `cross_tick.json` | north | vendor_graph | period0–period1 window |
| `period_failover.json` | north | vendor_graph | restore at period 4 with replay |

Optional profile fields: `checkpoint_out`, `warm_checkpoint`, `run_mode`, `failover_period`.

**period_failover** runs restore a captured period snapshot, trim staged invoice rows using merged period frontiers, then replay from the restored **resume period** cursor through the failover boundary before continuing. A correct run matches an uninterrupted **vendor_graph** audit on the same panel and geometry.

## Runner

The `vendorlab` binary accepts `--config <profile.json>` and `--out <output.json>`.
`tools/runner.sh` builds the binary when needed and invokes it with those flags.

```bash
bash /app/environment/tools/runner.sh <profile.json> /app/output/vendor_audit.json
```

Example invocations used in verification:

```bash
bash /app/environment/tools/runner.sh /app/environment/profiles/burst.json /app/output/vendor_audit.json
bash /app/environment/tools/runner.sh /app/environment/profiles/steady.json /app/output/vendor_audit.json
bash /app/environment/tools/runner.sh /app/environment/profiles/relay.json /app/output/vendor_audit.json
bash /app/environment/tools/runner.sh /app/environment/profiles/solo_stream.json /app/output/vendor_audit.json
bash /app/environment/tools/runner.sh /app/environment/profiles/mixed_fleet.json /app/output/vendor_audit.json
bash /app/environment/tools/runner.sh /app/environment/profiles/delay_ticks.json /app/output/vendor_audit.json
bash /app/environment/tools/runner.sh /app/environment/profiles/south_relay.json /app/output/vendor_audit.json
bash /app/environment/tools/runner.sh /app/environment/profiles/cross_tick.json /app/output/vendor_audit.json
```

Panel fixtures live under `/app/environment/fixtures/corpus_<panel_id>.json`.

Verifier-side variant configs may be written under `/tmp/vendor_variants/` when tests override profile fields. Warm-checkpoint and replay tests write ledger files under that directory (for example `warm_prefix.ckpt`, `replay_a.ckpt`, `replay_b.ckpt`, `entrypoint_prefix.ckpt`, and `lines_prefix.ckpt`); those paths are verifier scratch space, not part of the agent workspace contract.

## Experiment history context

Recent routing changes enabled multi-stage invoice tracking with deferred rollout settlement. line_item view flushes vendor exposure before the next funnel stage checks caps; vendor_graph view batches stages per period and may read stale committed totals until period boundary settlement—matching the phantom spend analysts see only after cross-vendor reconciliation.

## Container session recording

The image uses a custom Go base (`golang:1.22-bookworm`), not a Terminal-Bench pinned image. The Dockerfile preinstalls pinned `tmux` and `asciinema` and verifies them with `tmux -V` and `asciinema --version` so Harbor terminus-2 agent setup skips runtime package installs (which hang when `allow_internet=false`).

## Offline verifier policy

This task sets `environment.allow_internet = false` in `task.toml`. Pytest and `pytest-json-ctrf` are pinned in `environment/verifier-requirements.txt` and installed in `environment/Dockerfile` at image build time. `tests/test.sh` runs `python3 -m pytest` with `--ctrf` and writes `/logs/verifier/ctrf.json`; it must not download or install packages at verifier runtime.
