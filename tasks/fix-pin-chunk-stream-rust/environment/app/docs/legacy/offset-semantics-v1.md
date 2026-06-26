# Offset semantics (archived v1)

> Superseded by `offset-semantics.md`. Retained for soak regression notes.

Within a single schedule replay, the first staged drain advanced offsets by full `chunk_size` steps. Every later drain in that replay advanced by `chunk_size - 1` per emitted full chunk.

Probe tooling from that era assumed the shorter stride on second frames.
