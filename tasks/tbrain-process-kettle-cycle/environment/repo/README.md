# kettleheat

`kettleheat` is an offline, deterministic immersion process-kettle element ledger.
It reads one JSON document describing controller parameters and an ordered
kettle-temperature / power-mode event log, replays an anti-short-cycle heating
element controller, and prints the reconstructed element-ON intervals as JSON.

```
kettleheat < log.json
kettleheat log.json
```

See `docs/spec.md` for the full input format and the control/interval contract.

## Build

```
cargo build --release
```

The binary is written to `target/release/kettleheat`. The crate source lives under
`src/`.
