# Build and verify targets

## Binary

```
/app/bin/auditor --data <data-dir> --out <output-file>
```

* `--data` default `/app/data`
* `--out` default `/app/output/report.json`

Exit code 0 on success. Non-zero on any I/O or strict-type setup
error.

## Environment variable redirects

The binary honors two environment variables when present:

* `TWAMP_AUDIT_DATA_DIR` overrides `--data`.
* `TWAMP_AUDIT_OUT_PATH` overrides `--out`.

The verifier uses these to re-invoke the binary against the alt
fixture under `/tests/fixtures/alt_data/` and a temp output path.

## Build

```
cd /app && make build
```

produces `/app/bin/auditor`. The Go toolchain is preinstalled at
`/usr/local/go/bin` and is already on `PATH` in every shell context
(login, non-login, env-stripped). No network access is required for
the build; `GOTOOLCHAIN=local` and `GOPROXY=off` are baked in.

## Fast feedback loop

For quick iteration without paying the full pytest cost, the
Makefile ships two extra targets:

| Target        | Effect |
|---------------|--------|
| `make run`    | rebuild and run the auditor against `/app/data`; print exit code and the contents of `/app/output/` |
| `make verify` | rebuild, run, and pretty-print a one-line summary of `total_probes`, `aligned_good`, `cycles`, the full `by_verdict` map, the full `jitter_share_permille` map, the `report_digest`, and the per-cycle threshold ladder |

`make verify` is the fastest spot-check for cascade compounding. A
passing implementation prints, on the primary fixture:

```
cycle thresholds: [(0, 800), (1, 400), (2, 200)]
```

A naive cascade prints `(0, 800), (1, 400), (2, 400)` instead — the
800/400/400 ladder is the canonical signature of the "halve from
default" misimplementation.
