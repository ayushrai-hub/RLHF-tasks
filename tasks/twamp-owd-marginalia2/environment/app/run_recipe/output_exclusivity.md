# Output directory exclusivity

`/app/output` is the only directory the auditor writes to. Before
writing a fresh `report.json`, the emitter MUST clear every direct
child of `/app/output`. The cleanup is unconditional and recursive:

* Regular files OTHER than the freshly written report must be
  removed.
* Subdirectories must be removed in full, including their contents.
* Symlinks count as direct children and must be unlinked.

A "regular files only" filter (`if isFile`, `if mode.IsRegular()`,
etc.) is insufficient. A stale subdirectory survives that filter
and causes the post-run listing to contain more than `report.json`.

## Before and after

Before the run, `/app/output` may contain leftovers from a previous
run, an interactive session, or a debugger:

```
/app/output/report.json
/app/output/report.json.bak
/app/output/stale_dir/
/app/output/stale_dir/leftover.json
```

After the auditor finishes, the directory MUST look like:

```
/app/output/report.json
```

A correct implementation uses an unconditional recursive remover
(`os.RemoveAll`, `shutil.rmtree`, `rm -rf`) on every direct child of
the output parent, then writes the new report atomically.

## Determinism contract

The exclusivity rule is part of the determinism contract:

* Re-running the binary with the same input produces byte-identical
  output (`B1` idempotency).
* The output directory contains exactly one file: `report.json`
  (`B2` exclusivity).
* Stale files AND stale subdirectories under `/app/output` are
  removed by the auditor on each run (`B3`).
* Building from a clean state (`rm -rf /app/bin && make build`)
  produces a working binary (`B4`).
* No lockfile or module-mode flag bypass: the build is fully
  module-aware (`B5`).
