All digest fields are 16-hex sha256 prefixes. Independent recomputation may use `openssl dgst -sha256 -hex` on the documented byte strings and truncate to 16 hex characters.

## Output schema

Top-level envelope:

| Field | Type | Description |
|-------|------|-------------|
| `runs` | array | One row per scenario from `matrix_order.txt` |
| `report_digest` | string | 16-hex digest over canonical row envelopes |
| `replay_token` | string | 16-hex digest binding workspace to `report_digest` |

Each run row:

| Field | Type | Description |
|-------|------|-------------|
| `scenario` | string | Scenario identifier |
| `wave_gen` | int | Active archival gen after the scripted cycle |
| `edge_fp_host` | string | Host layered-view fingerprint |
| `edge_fp_work` | string | Work layered-view fingerprint |
| `miss_gap` | int | `host_visible - work_new_bytes` |
| `gen_skew` | int | `host_wave_gen - work_wave_gen` from `wave_gen` markers |
| `retention_stamp` | string | Archival body stamp for the active gen |
| `row_seal` | string | Per-row integrity seal |

## View fingerprint

```
edge_fp_host = hex(sha256("host|" + host_view_bytes))[0:16]
edge_fp_work = hex(sha256("work|" + work_view_bytes))[0:16]
```

`host_view_bytes` is the full body of `layers/host/active.log`.
`work_view_bytes` is the full body admitted by the work-view authority.

Each row's fingerprints are captured when that scenario finishes inside the driver, before the next scenario resets the workspace. They hash the layered view bytes present at that moment — not the workspace tree left behind after later scenarios. For `wave_once`, closing `batch_a` at generation 1 advances layered views to generation-2 `active.log` material while the row still records `wave_gen` 1.

## Generation skew

```
host_wave_gen = integer read from layers/host/wave_gen (default 1 if missing)
work_wave_gen = integer read from layers/work/wave_gen (default 1 if missing)
gen_skew = host_wave_gen - work_wave_gen
```

After coordinated repair, every scenario row must report `gen_skew` equal to zero. A non-zero skew means host-side generation markers advanced without the work-view authority — a delayed symptom that can persist even when byte-length probes look aligned.

## Marker recycle

Scenarios that call `watch/recovery.RecycleMarkers` expect a full realignment of work-view state from the host view after an observer pause: both `active.log` body bytes and the `wave_gen` marker file must be copied from `layers/host/` into `layers/work/`. Scenarios that omit recycle (see `stale_marker`) rely on batch close to keep both markers aligned.

## Published entry probe

After each rename batch close, `published/` must hold one regular file for every regular file in the matching fixture generation directory under `fixtures/wave/gen{N}/`. That includes `active.log` and the batch metadata JSON for the closed batch (`batch_a.json` at generation 1, `batch_b.json` at generation 2). Only the current batch metadata file should remain in `published/` after a close (older `batch_*.json` entries are replaced).

Entry-probe cardinality compares the regular-file count under `published/` to the regular-file count in `fixtures/wave/gen{N}/` for the row's `wave_gen` when evaluating the `wave_once` scenario after a full audit.

## Byte gap

```
host_visible = byte length of layers/host/active.log
work_new_bytes = byte length of layers/work/active.log
miss_gap = host_visible - work_new_bytes
```

When authorities agree after a coordinated repair, `miss_gap` is zero for every scenario.

## Scenario expectations

After coordinated repair, each scenario row reports:

| Scenario | wave_gen | recycle called |
|----------|----------|----------------|
| wave_once | 1 | yes |
| wave_twice | 2 | yes (after each batch) |
| pause_trap | 2 | yes (after reopen batch) |
| stale_marker | 1 | no |

All scenario rows must show `miss_gap` and `gen_skew` equal to zero.

## Body stamp

```
retention_stamp = hex(sha256(str(wave_gen) + "|" + fixture_body))[0:16]
```

`fixture_body` is the raw bytes of `fixtures/wave/gen{N}/active.log` for the row's `wave_gen`.
The stamp must not be derived from pathname size alone.

## Row seal

Canonical row pipe-fields in order:

```
scenario|wave_gen|edge_fp_host|edge_fp_work|miss_gap|gen_skew|retention_stamp
```

```
row_seal = hex(sha256(canonical_row))[0:16]
```

## Report digest

For each row, build a canonical fragment:

```
scenario;wave_gen;edge_fp_host;edge_fp_work;miss_gap;gen_skew;retention_stamp;row_seal
```

Sort fragments lexicographically, join with newline, then:

```
report_digest = hex(sha256(joined_fragments))[0:16]
```

## Replay token

```
replay_token = hex(sha256(report_digest + "|" + workspace_root))[0:16]
```

`workspace_root` is the `--workspace` flag value (default `/app/data/workspace`).

## Idempotency rule

Two consecutive arrival-audit audits on an unchanged workspace tree must yield identical `report_digest` and `replay_token`.
