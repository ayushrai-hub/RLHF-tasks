# thermalwatch

A small offline command-line transformer-thermal compliance engine. It replays a
piecewise-constant stream of transformer temperature readings against
per-asset limits with arm/clear dwell timers, service windows, and a
cumulative over-time budget, and prints a deterministic JSON ledger of confirmed
temperature excursions, cumulative confirmed over-time, a one-way insulation-failure
instant, and each asset's final state at the horizon.

```
go build -o thermalwatch ./cmd/thermalwatch
./thermalwatch < scenario.json > ledger.json
```

The required behavior — the piecewise-constant temperature model, the
arm/debounce confirmation, the clear/recovery dwell with sub-clear dip merging,
the service window that pauses the dwell and over-time clocks, the cumulative
over-second budget with its interpolated one-way insulation-failure latch, the final
state, and the canonical output ordering — is described in
[docs/spec.md](docs/spec.md).
The decision logic lives in
[internal/engine/engine.go](internal/engine/engine.go); `cmd/thermalwatch/main.go`
only handles standard input/output and the process exit status.
