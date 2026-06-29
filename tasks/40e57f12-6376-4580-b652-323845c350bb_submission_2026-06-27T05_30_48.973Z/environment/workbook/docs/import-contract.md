# Import contract

Read nested sweep JSON from `/app/workbook/fixtures/sweeps/*.json` in ascending lexicographic filename order. When the same `meta.run.id` appears in multiple files, the last processed file wins.

Each file stores `meta.run.id`, `meta.run.kernel`, `params.dt`, `params.dimension`, optional `params.fit_lag_min` / `params.fit_lag_max`, and MSD samples under `series.msd[]` with fields `step` and `msd`.

Insert one row into `sweeps` and one row per lag into `msd_points`. Persist `fit_lag_min` and `fit_lag_max` from fixture params, defaulting to 2 and 5 when omitted.

`kernel_revision` must be the effective module path and version after following every `replace` directive in the workspace module's `go.mod` under `/app/workbook/kernels/`, including chained replacements across local modules. Format: `<module-path>@v<version>` using the final target module path and version (not the wrapper module name). Implement resolution in `/app/workbook/lib/go-resolve.js`.

Skip files whose `meta.run.id` is missing. Ignore `/app/workbook/kernels/README.md` and `kernel-registry.toml` for revision selection — this contract is authoritative.
