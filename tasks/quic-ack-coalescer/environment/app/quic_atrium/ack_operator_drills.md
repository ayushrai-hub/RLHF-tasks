# Runbook

## Build

```
cd /app
make build
```

The build produces `/app/bin/qack`. `GOTOOLCHAIN=local` and `GOPROXY=off` are
pinned by the image so the build never tries to fetch a module. The build
takes roughly a second on a warm cache.

## Run against the primary fixture

```
/app/bin/qack
```

Reads `/app/ack_trove` and writes `/app/output/report.json`. Stdout is empty on
success. Nonzero exit code indicates a load-time failure or a write failure;
the reason is on stderr.

## Run against the sample harness

```
QACK_DATA_DIR=/app/quic_atrium/ack_workshop/coalescer_seed \
QACK_OUT_DIR=/tmp/qack-sample \
/app/bin/qack && diff -u /app/quic_atrium/ack_workshop/golden_run.json /tmp/qack-sample/report.json
```

A byte-clean diff confirms the binary's window math, sort orders, JSON
formatting, and digest scheme are aligned with the schema.

## Re-run determinism

Running the binary three times in a row writes the same bytes every time. A
quick check:

```
/app/bin/qack
sha256sum /app/output/report.json
/app/bin/qack
sha256sum /app/output/report.json
/app/bin/qack
sha256sum /app/output/report.json
```

All three hashes are identical when the binary is correct.

## Output cleanup

`/app/output` is emptied at the start of every run. A stale file dropped into
that directory between runs disappears as soon as the binary executes; it does
NOT survive to the next report.

## Failure modes

* Missing or unreadable shard file — the binary exits nonzero with the OS
  error on stderr.
* A frame with a malformed JSON line — the binary exits nonzero; the report
  is not written.
* No frames at all — the binary still writes a well-formed report with zero
  totals, all closed-enum keys present, and the digest computed over the
  empty-event canonical bytes.
* An invalid `urgent` field on a connection (non-boolean) — the binary exits
  nonzero on connection-load.

## Sanity checks

* `summary.total == len(events)`.
* For every `by_conn[i]`, `events_count == sum(by_conn[i].by_verdict.values)`.
* `summary.by_verdict[v] == sum_over_conns(by_conn[i].by_verdict[v])`.
* `sum(hamilton[i].basis_points) == 10000` when total weight > 0.
* `report_digest` recomputes to itself when re-hashing the report with the
  digest field blanked.

If any of those break, the bug is upstream of the sanity checks — fix the
producing stage, not the check.
