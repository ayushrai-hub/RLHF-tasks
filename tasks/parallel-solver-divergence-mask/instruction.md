The `tb_iter` driver at `/usr/local/bin/tb_iter` reads `/app/data/cases.csv` and writes `/app/output/report.json` and `/app/output/run_meta.json`. Small smoke runs pass, but results still change when you sweep workers from 2 to 10 on the same seed: `fold_token`, `dispersion_score`, `audit_chain`, `objective`, and asset weights do not stay put. `continued` mode with checkpoints and a run journal has its own bugs — wrong `phase_id` after hops, journal tails that should fail but do not, dispersion rounded away on checkpoint reload, and continued runs that disagree with a fresh run for the same seed.

Fix the C++ tree under `/app/environment`, rebuild `tb_iter`, and bring behavior in line with `/app/docs/report_contract.md`. Leave `/app/data/cases.csv` alone.

Rebuild before checks:

`rm -rf /app/build && cmake -S /app/environment -B /app/build -DCMAKE_BUILD_TYPE=Release && cmake --build /app/build --parallel 1 && cp /app/build/tb_iter /usr/local/bin/tb_iter`

For one seed and dataset, outputs must match across workers 2–10 and between `fresh` and `continued` when the checkpoint is valid. Mismatched seed, workers, or journal state must exit non-zero. Each journal hop must bump `phase_id` by one; long save/continue chains must land on the same report as a single fresh run. Checkpoints must write dispersion with full `double` precision. Optional layout flags must not change the numeric report. Hand-written JSON without a rebuilt binary will not pass.
