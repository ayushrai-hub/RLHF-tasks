# Seglog service

The crate under /app/environment simulates transfer batches through a ledger engine, checkpoint framing, durable stream helpers, and a three-branch matrix driver. Scenario timing indices live in config/bundles.toml and are mirrored in src/sim/case.rs. See layout_notes.md for how those modules connect to the Cargo tree.

Each bundled scenario runs three ways. Continuous applies batches without interruption. crash_resume seals a checkpoint at save_at inside a multi-leg batch (at checkpoint_leg), restores, and finishes. compaction_replay seals, folds stream records whose step falls in (save_at, compact_at], restores, replays the folded segment, and applies later batches live.

Checkpoints capture pot balances, retired markers, staged move legs, and the sequence counter.

tools/run_matrix.sh renders the full report to /app/output/ledger_report.json. tools/run_subset.sh renders a comma-separated scenario list. tools/divergence_probe.sh exits non-zero when forced branches diverge from continuous for one scenario. ci/matrix_regress.sh replays subsystem regression traps against the live sources.
