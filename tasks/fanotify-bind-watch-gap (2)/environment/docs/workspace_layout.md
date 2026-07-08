# Workspace layout

The arrival-audit driver materializes layered views under `/app/data/workspace`:

- `layers/host/active.log` — host-side layered view body
- `layers/work/active.log` — work-view authority body
- `layers/host/wave_gen` and `layers/work/wave_gen` — active wave generation markers
- `published/` — bind-layer sink and entry-probe directory (see audit_contract.md)
- `archive/gen{N}/` — archived bodies per closed rename batch

Fixture batches live under `/app/environment/fixtures/wave/gen{N}/` (`active.log` plus `batch_*.json` metadata).

Scripts under `/app/environment/scripts/` populate and exercise these paths:

- `setup_fanout.sh` — bootstrap layered views from gen1 fixtures
- `run_wave.sh` — reset workspace and seed fan-out
- `write_load.sh` — append synthetic producer traffic to the published sink
