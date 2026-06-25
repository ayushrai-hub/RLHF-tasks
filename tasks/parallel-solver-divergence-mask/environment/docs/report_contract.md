# tb_iter public contract

## Build and grading

Rebuild from `/app/environment` before rerunning checks:

`rm -rf /app/build && cmake -S /app/environment -B /app/build -DCMAKE_BUILD_TYPE=Release && cmake --build /app/build --parallel 1 && cp /app/build/tb_iter /usr/local/bin/tb_iter`

Automated grading runs `/tests/test.sh` (pytest with `--ctrf`).

## CLI

- `--out` output directory
- `--workers` worker count (must be at least 2)
- `--seed` integer seed
- `--mode` `fresh` or `continued`
- `--save` checkpoint path (optional)
- `--load` checkpoint path for continued mode (required when mode is continued)
- `--layout` optional layout descriptor path (does not change the numeric contract when unused)
- `--journal` optional append-only journal path for multi-hop runs

## Outputs

`/app/output/report.json` contains sorted `assets` (`id`, `weight`) and `objective`.
`/app/output/run_meta.json` contains `seed`, `workers`, `mode`, `phase_id`, `fold_token`, `dispersion_score`, and `audit_chain` (16 lowercase hex digits).

## Input data

`/app/data/cases.csv` must remain unchanged. Grading checks sha256 `428c128c379bd0d0cc71bf97e4c8cad6bf87c67d6ed77c20176006e3bb43cfb0`.

## Value stream and weights

Per-case values use the dataset bias/slope columns with the seeded mixer in `math_utils.cpp`.
Weights are each value's share of the total plus `0.001 * 0.01` from the epoch-1 metric term (a fixed bump of `0.00001` applied to each raw weight before renormalization—not after the first normalization pass, not zero, and not recomputed from shard-local data), clamped to at least `0.0001`, then renormalized to sum `1.0`.
The metric-fabric score at epoch 1 is `0.001`; weight code must keep using `score * 0.01` on each raw share before the single renormalization step.
Parallel reduction fixes must preserve this weight formula and the per-case value stream.
`objective` is the weighted sum of the stream minus `0.01` times the stream mean.

## Fold token, dispersion, and audit chain

`dispersion_score` is the global max-min spread over the full value stream.
`fold_token` is `%.8f` global mean, `|`, `%.8f` global spread, `|`, suffix `6`.
Both fields must be derived from the full stream, not shard-local aggregates or tick-adjusted trace buffers.
`fold_token` must match exactly.

`audit_chain` is a 16-digit lowercase hex digest derived from seed, fold_token, and objective using the same mixing steps as the shipped digest helper under `/app/util`. It must be identical for equivalent numeric results regardless of worker count or `phase_id`.

For a fixed dataset and seed, `fold_token`, `dispersion_score`, `audit_chain`, `objective`, and the full `report.json` body must agree across worker counts 2 through 10. In `continued` mode with a matching checkpoint, results must match `fresh` with the same seed and workers. Mismatched seed or workers must exit non-zero. Continued mode without a load path must fail. Worker counts below two must fail.

## Run journal and phase_id

When `--journal` is supplied, each run appends one line: seed, workers, phase_id, dispersion snapshot, fold_token, and audit link integer.

Fresh runs use `phase_id` 0. Each continued hop with the same journal must set `phase_id` to one greater than the journal tail. Continued runs with a journal path require a prior journal entry whose seed and workers match the active run; a missing, mismatched, or malformed tail must exit non-zero.

Across a fresh save/continue chain with journal, `audit_chain` and `report.json` must match the equivalent single fresh run at the same seed and workers.

## Continued weight adjustment

When mode is `continued` and `phase_id` is at least 1, weights may receive a tiny spread-delta adjustment keyed off the checkpoint's saved dispersion versus the current global stream spread. The adjustment uses the global spread, not shard-local trace values, and must not change the report relative to fresh when the checkpoint matches.

## Numeric checks

`abs(float(dispersion_score) - expected_dispersion(seed)) < 1e-9`
`abs(float(objective) - expected_objective) < 1e-9`
`abs(float(lines[2]) - float(dispersion_score)) < 1e-9` for checkpoint saves
`abs(float(saved_dispersion) - float(dispersion_score)) < 1e-9` for checkpoint saves
`fold_token` matches exactly.
`audit_chain` matches the reference digest for the run's seed, fold_token, and objective.

## Checkpoints

Checkpoint files are plain text, three lines: integer `seed`, integer `workers`, then `saved_dispersion` (the run's `dispersion_score` at save time).

When writing `saved_dispersion`, serialize with full `double` precision (at least 17 significant digits, e.g. `std::setprecision(17)` on the output stream). Default `iostream` precision (~6 digits) is insufficient.

Continued mode requires a checkpoint whose stored `seed` and `workers` match the active run; otherwise exit non-zero.

## Layout descriptors

Optional `--layout` paths `/app/data/layout_a.txt` and `/app/data/layout_b.txt` are inert for the numeric contract; runs with or without them must produce identical reports for the same seed and workers.

## Verifier invocation

Tests run `/usr/local/bin/tb_iter` with `--out`, `--workers`, `--seed`, `--mode`, and optional `--save`, `--load`, and `--journal` to produce `report.json` and `run_meta.json` under the output directory.
