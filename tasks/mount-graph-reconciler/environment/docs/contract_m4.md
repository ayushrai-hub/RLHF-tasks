# contract_m4

Graded output: `/app/output/graph_report.json` from `/app/bin/mgr_run --matrix --out /app/output/graph_report.json`.

`/app/bin/mgr_run` is the matrix checker CLI: when invoked with `--matrix`, it must walk each scenario arm in the table below, reconcile authoritative edge slices against the tab layout, and report one graded row per arm in the output JSON.

Rebuild packages with `/app/environment/scripts/bake_m4.sh` before running the checker.

## Cleanup command

Run before each graded audit when prior runs may have left stage state:

```bash
bash /app/environment/migrations/cln_m4.sh
```

This command is idempotent. It removes `/app/output/graph_report.json` and `/app/output/.mgr_stage/`, then creates a fresh `clean_mark` file under `.mgr_stage/`.

## graph_report.json schema

Top-level fields:

- `schema_ver` (string): always `m4`
- `arms` (array): one object per scenario arm
- `run_token` (string): sha256 hex of arm `row_digest` values joined with `|`

Each arm object:

- `arm_id` (string field): scenario label for the arm
- `cl_tag` (string): cluster label `c0`, `c1`, or `c2`
- `row_digest` (string): sha256 hex per formula below
- `node_tags` (array of strings): sorted `key+cl_tag` for alive slots only
- `path_a_hex` (string): sha256 hex of sorted `key:marker` slot map
- `path_b_hex` (string): sha256 hex of concatenated node tag strings
- `cross_link` (string): sha256 hex of `path_a_hex|path_b_hex|cl_tag`

## Row digest formula

```
row_digest = sha256(cl_tag + "|" + join(sorted(node_tags), "|") + "|" + cross_link)
```

## Scenario matrix

| arm_id | cl_tag | edge slice |
|--------|--------|------------|
| c0_base | c0 | c0_a.grf |
| c1_var | c1 | c1_a.grf |
| c2_var | c2 | c2_a.grf |
| c0_repeat | c0 | c0_a.grf (repeat pass) |
| c1_repeat | c1 | c1_a.grf (repeat pass) |
| c2_repeat | c2 | c2_a.grf (repeat pass) |

## Stage stub semantics

`/app/environment/fixtures/stage_stub/m3_stub.json` exposes per-cluster `alive_count` fields that summarize interim live edges. Report `node_tags` cardinality must fall below `alive_count` when retired markers were stripped from graded arms.

All digest fields are lowercase sha256 hexdigest strings computed with the formulas above. All string inputs to sha256 are encoded as ASCII bytes before hashing.

## Distributed consistency

Graded arms require **distributed consistency** between the tab fragment layout (`/app/environment/fixtures/tab_frag/fs0.tab`) and authoritative edge slices per cluster. Summary JSON under `/app/environment/fixtures/unit_snap/` may align on counts while propagation bytes still disagree.

## Repeat-cycle arms

Repeat arms exercise **replay semantics**: within one matrix run, repeat arms must re-compute identical digests for the paired arm without inheriting stale stage state from a prior invocation.

Repeat arms are produced within the **same** full-matrix invocation as their paired arms.

### Within one clean run

After cleanup, a single `--matrix` invocation must satisfy:

- `c0_repeat` matches `c0_base` on `path_b_hex`, `cross_link`, and `row_digest`
- `c1_repeat` matches `c1_var` on the same fields
- `c2_repeat` matches `c2_var` on the same fields

### Across invocations

- After cleanup, two consecutive full-matrix runs (each preceded by cleanup) must produce identical `run_token` values and identical `row_digest` for every arm.
- If a full-matrix run succeeds and cleanup is **not** rerun, the **next** full-matrix invocation must exit with non-zero status (cycle guard).
