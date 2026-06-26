# Digest format

Each emitted chunk is one line:

```text
<offset>:<digest>
```

`offset` is the zero-based byte index where the chunk begins in the schedule payload.

`digest` is FNV-1a over the chunk bytes, rendered as eight lowercase hex digits. Limb selection for tails vs full chunks is defined in `chunk-contract.md`.

Full chunks contain exactly `chunk_size` bytes from `/app/config/stream.json`. Payloads that are not an even multiple of `chunk_size` end with one shorter tail chunk.

Digest lines for a schedule must be in ascending `offset` order with no gaps.
