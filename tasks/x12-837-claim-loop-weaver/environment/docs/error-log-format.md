# Error log format

Each skipped segment produces one line in `/app/output/errors.log`:

```text
<shard-basename>: <original segment text>
```

The segment text must match the raw bytes read from the shard file — no trimming, case changes, or delimiter normalization.

Lines sorted alphabetically by the full line string.
