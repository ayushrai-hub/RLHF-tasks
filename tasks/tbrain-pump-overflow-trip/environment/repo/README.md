# overflow

A small offline command-line pump-station overflow protection engine. It replays a
piecewise-constant stream of per-line flow (lps) samples against per-line
flow ceilings with arm/reset dwell timers, maintenance windows, and a cumulative
trip-second budget, and prints a deterministic JSON ledger of confirmed overflow
trips, cumulative confirmed trip-time, a one-way lockout instant, and each
line's final state at the horizon.

```
go build -o overflow ./cmd/overflow
./overflow < scenario.json > ledger.json
```

The required behavior — the piecewise-constant flow model, the arm/debounce
confirmation, the reset/recovery dwell with sub-reset dip merging, the
maintenance window that pauses the dwell and trip clocks, the cumulative
trip-second budget with its interpolated one-way lockout latch, the final state,
and the canonical output ordering — is described in [docs/spec.md](docs/spec.md).
The decision logic lives in
[internal/engine/engine.go](internal/engine/engine.go); `cmd/overflow/main.go`
only handles standard input/output and the process exit status.
