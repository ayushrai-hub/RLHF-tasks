# Replay epoch

Each `integrate-shot` assigns a monotonic **`replay_seq`** for the `(stack, seed)` pair and persists it in `/app/state/shot-snapshot.json`. Counters live in `/app/state/replay-history.json` (created on first integrate).

- First integrate for `multi-layer` + seed `42` → `replay_seq = 0`
- Second integrate with the same stack name and seed (without clearing history) → `replay_seq = 1`

`trace_digest` in export JSON hashes **`{replay_seq}|{id1,id2,...}`** where ids are `trace_ids` in traversal order (no sorting). The replay epoch integer must appear **before** the pipe, not after the id list. Example: replay `1` with ids `[103,101,102]` → SHA-256 input `"1|103,101,102"`.

Export must read `replay_seq` from the staged snapshot file, not recompute it. Clearing `/app/state/` resets history.
