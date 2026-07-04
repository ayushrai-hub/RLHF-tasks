# Bundled hive-scale fixtures

These files support manual exploration only. Verifier cases generate fresh temporary
manifests and streams under pytest `tmp_path`.

- `manifests/demo_part1.json` and `demo_part2.json` split a two-stream schedule for resume checks.
- `manifests/demo_full.json` replays both primary streams in one run.
- `streams/demo_a.hws2` and `demo_b.hws2` hold v2 `HWS2` sample frames.
- `streams/demo_backfill.hws2` repeats an event id for duplicate/idempotence experiments.
- `streams/legacy_v1.hsf` holds legacy `HWSC` v1 bytes for unsupported-format handling.
