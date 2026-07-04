# Repository layout

The Cargo crate root is /app/environment/src. Replay drivers, checkpoint codecs, journal helpers, and the branch matrix live as top-level modules under /app/environment/core, /app/environment/codec, /app/environment/journal, and /app/environment/flow. They are wired into the crate through path attributes in src/sim/mod.rs; replay logic is not nested under src/sim.

The sim package under src/sim owns the scenario catalog and JSON rendering. Scenario timing indices are in /app/environment/config/bundles.toml and mirrored in src/sim/case.rs. Subset order for harness runs is in /app/environment/ci/sequences.json.

Shell wrappers under /app/environment/tools drive full-matrix runs, subset rendering, per-scenario branch probes, checkpoint round-trip checks, and compaction idempotency probes. /app/environment/ci/matrix_regress.sh replays subsystem regression traps against the live sources.
