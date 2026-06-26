# Offset semantics

Each digest line's `offset` field is the byte index in the original schedule payload where that chunk begins.

Offsets advance by `chunk_size` for every full chunk. The tail chunk's offset is the index of its first byte (the remainder after full chunks).

`streamd probe-one` prints comma-separated offsets in digest-line order. Those values must match the offsets printed by `replay-one` for the same schedule.
