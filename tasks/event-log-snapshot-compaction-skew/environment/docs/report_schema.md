# Ledger report JSON

The matrix runner writes /app/output/ledger_report.json.

Top level: report_version is the format version (currently 1). runs holds one object per bundled scenario in the main matrix.

Each run object includes scenario (scenario id), seq_high_water (highest sequence counter observed across branches in that run), and branches (observations for continuous, crash_resume, and compaction_replay).

Each branch object includes branch (branch name), aggregate_digest (32-character lowercase hex derived from pot balances and retired-key counts), event_digest (16-character lowercase hex over the ordered entry lines), seq_high_water (highest sequence number in this branch stream), checkpoint_bytes (byte length of the sealed checkpoint, zero on continuous), fold_records (how many stream records compaction replay folded, zero on continuous and crash_resume), and entries (ordered durable lines).

Each entry is one string with pipe-separated fields: seq|acct|kind|val|step. The renderer zero-pads seq and acct in output.

Main report scenarios (six runs): copper_wire_fan, nickel_merge_lane, slate_purge_arc, brass_split_ladder, iron_cross_weave, mercury_gate_fold. Subset probes not listed in the six-run main report: quartz_ledger_skew, obsidian_tail_fold.

For a given scenario, branches are equivalent when aggregate_digest, event_digest, seq_high_water, and entries all match. Forced branches that sealed a checkpoint share the same checkpoint_bytes. Compaction replay is the branch that reports fold_records above zero.
