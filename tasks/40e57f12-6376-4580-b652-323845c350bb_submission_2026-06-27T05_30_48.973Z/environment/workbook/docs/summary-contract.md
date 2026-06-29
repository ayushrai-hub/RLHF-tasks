# Summary contract

For each sweep in `sweeps`, compute mean-squared-displacement diffusion coefficient `D` and residual sum of squares `rss`.

Use the per-sweep fit window stored in `fit_lag_min` and `fit_lag_max` (inclusive lag steps from `msd_points`). For dimension `d`, timestep `dt`, and lag step `k`, the model is:

`MSD(k) = 2 * d * D * k * dt`

Let `x = 2 * d * k * dt` for each lag in the fit window. Fit `D` by ordinary least squares **through the origin** (zero intercept):

`D = sum(MSD * x) / sum(x * x)`

Predicted values are `predicted = D * x`. Round `D` and `rss` to six decimal places before insert.

`rss` is the sum of squared residuals `(observed_msd - predicted)^2` across the fit points only. Implement the fit helper in `/app/workbook/lib/msd.js`.

Write one row per sweep into `diffusion_summary` with matching `kernel_revision`.
