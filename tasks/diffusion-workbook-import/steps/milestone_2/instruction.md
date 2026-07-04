Import looks fine now, but `/app/workbook/migrations/002_summary.js` writes bad diffusion coefficients and RSS values into `diffusion_summary`, and `/app/workbook/lib/msd.js` is missing the per-sweep lag-window fit helper.

Fix both per `/app/workbook/docs/summary-contract.md` using the sweeps already in `/app/workbook/data/workbook.sqlite`. Each sweep stores its own `fit_lag_min` / `fit_lag_max`. Run `/app/workbook/bin/migrate.sh` when finished.
