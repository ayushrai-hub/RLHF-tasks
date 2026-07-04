# Exit table policy

All movement validation must query `room_exits` in SQLite. Hard-coded adjacency maps are forbidden. Directions are lowercase (`east`, `north`, `south`, `west`). `requires_key = 1` means the exit stays blocked until `UNLOCK <direction>` succeeds while `has_key` is set.
