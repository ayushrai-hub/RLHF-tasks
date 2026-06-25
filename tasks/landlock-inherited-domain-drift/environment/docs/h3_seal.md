# matrix seal

After emit, `/app/environment/tooling/seal_trace.sh` writes `summary.matrix_seal` on `/app/output/h7_trace.json`.

## Algorithm

Use FNV-1a 64-bit with basis `14695981039346656037` and prime `1099511628211`. Hash the UTF-8 payload built from **emit-order** rows (same order as `h3_contract.md`):

For each slot in order (`w0_short/direct`, `w0_short/svc`, `w0_long/direct`, `w0_long/svc`), append one line:

```
{profile}|{principal}|{reach_digest}|{chain_seq}\n
```

The `matrix_seal` field is the 16 lowercase hexadecimal characters of the hash (zero-padded).
