# Ledger state

Pot balances are keyed by numeric account ids. Retired ids are excluded from balance totals but remain visible in the durable stream as retire records.

Multi-leg batches may stage move legs until an explicit close leg or batch end triggers a flush. Each bundled scenario carries timing indices in config/bundles.toml and src/sim/case.rs: steps, save_at, checkpoint_leg, resume_from, and compact_at.

Checkpoints taken at save_at are captured mid-batch at checkpoint_leg before later legs in that batch run. Staged in-flight moves, pot balances, retired ids, and the sequence counter should round-trip through seal and restore without dropping batch staging state.

Compaction replay folds durable stream records whose step falls in (save_at, compact_at] before restoring and replaying the folded segment. Live steps after compact_at are applied on top of the restored state.
