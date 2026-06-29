# Batch contract

`simulate-batch` reads `/app/fixtures/batches/<name>.json` with an `events` array. Each event includes `sim_tick`, `shot_id`, stack path, velocity, and energy.

Export shape:

```json
{
  "batch": "tick-order-trap",
  "ticks": [
    { "sim_tick": 0, "hits": [ ... ] },
    { "sim_tick": 2, "hits": [ ... ] }
  ]
}
```

Group events by `sim_tick`, sort tick groups by ascending `sim_tick`, and within each tick sort hits by ascending `shot_id`. Do not flatten hits in file arrival order.

Each hit entry mirrors single-shot exports plus `shot_id` and `sim_tick`.
