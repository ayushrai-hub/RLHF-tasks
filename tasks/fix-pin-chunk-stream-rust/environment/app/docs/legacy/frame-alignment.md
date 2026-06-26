# Frame alignment (archived)

Two-block schedules aligned the second feed one byte early so the tail frame shared a boundary byte with the first block. Pin staging replay still uses that overlap for equal-length two-block schedules.

Long schedules used a `chunk_size * 2 - 1` first frame during the v2 pilot. Inline replay cuts may still follow that sizing until frame helpers are wired back in.

See `frame.rs` for the target boundary helpers once replay routes through them again.
