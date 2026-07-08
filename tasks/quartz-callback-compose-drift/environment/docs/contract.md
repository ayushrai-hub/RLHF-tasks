# ODE callback compose contract

## Inputs

`ode_plan.tbl` header: `tag|y0|dt|steps|callback_order|restart_step`. Rows are processed in file order. `restart_step` is a zero-based step index, or `-1` when no restart is configured.

`callback_order` lists semicolon-separated `name:load_order` pairs such as `hook_a:2;hook_b:1`. Callback names must exist in `hooks.tbl`. Registration order is the left-to-right index in the string.

`hooks.tbl` header: `name|threshold|on_fire`. `on_fire` is `none`, `add:VALUE`, `mul:VALUE`, or `set:VALUE` applied to `y` after a hook fires.

`ode_overlay.toml` keys:
- `tol` (positive float, default `1e-6`) — tolerance for restart eligibility when `y < tol` at `restart_step`.
- `metric_scale` (positive float, default `1.0`) — base multiplier for each trapezoid slice.
- `restart_target` (positive float, default `1.0`) — value assigned to `y` on tolerance restart.
- `carry_gain` (non-negative float, default `0.005`) — scales the prior row's `event_step` into the next row's effective metric multiplier.

## Checkpoint carry

`ode_checkpoint.json` in `/app/cfg` holds `last_event_step` (integer) from the immediately preceding plan row (`-1` before the first row). Before the first plan row of each harness run, initialize `ode_checkpoint.json` to `last_event_step = -1`. Before each plan row the harness reads this file; after the row completes it rewrites the file with that row's computed `event_step`.

For row index `i > 0`, effective metric scale is `metric_scale * (1 + carry_gain * last_event_step)` where `last_event_step` is the prior row's computed `event_step` (negative prior values contribute zero carry).

## Integration model

Model: `dy/dt = -y` with analytic solution `y(t) = y0 * exp(-t)`. Forward Euler uses `y_{n+1} = y_n - dt * y_n`.

Each integration step `i` from `0` to `steps-1`:
1. Remember `y_prev = y`.
2. Apply the Euler update.
3. If `i == restart_step` and `y < tol`, reset `y` to `restart_target` before callbacks.
4. Sort callbacks by ascending `load_order`; ties break by registration order (lower index first).
5. Invoke callbacks in sorted order. A hook fires when `y_prev < threshold <= y` on that step, or at step `0` when `y0 >= threshold`. Each hook is evaluated against the current `y` after any earlier callbacks on the same step have applied their `on_fire` effects; step `0` still uses `y0` for the threshold test. The first step where any hook fires becomes `event_step` (`-1` when none fire).
6. Accumulate `metric_integral` with the trapezoid rule: add `effective_scale * dt * (y_prev + y) / 2` using the step's start `y_prev` and final `y` after callbacks, where `effective_scale` includes carry from the checkpoint.

`order_sensitive` is true when the row's `callback_order` contains duplicate `load_order` values among its callbacks.

## Per-case audit flags

`euler_ok` when the Euler module matches the contract formula; `event_ok` when `event_step` matches hook crossings; `restart_ok` when tolerance restart used `restart_target`; `metric_ok` when `metric_integral` matches the scaled trapezoid sum; `summary_ok` when all sub-checks pass.

`report_line` is `ok` when `summary_ok` is true, otherwise `drift`.

Per-case audit recomputation is split across the `audit` modules; those modules must agree with the driver when the implementation is correct.

## Output artifacts

`ode_harness` writes `/app/output/run_summary.json` with top-level keys `schema_version`, `cases`, and `digest` only. `schema_version` is the string `run.v1`. Each case object contains exactly `tag` (string), `event_step` (integer), `metric_integral` (number), `order_sensitive` (boolean), `euler_ok`, `event_ok`, `restart_ok`, `metric_ok`, `summary_ok` (booleans), and `report_line` (string). `summary_ok` is the logical AND of the four sub-check booleans. The digest is `|`-joined per-case tokens `tag:event_step:metric_integral` in plan row order with `metric_integral` formatted to exactly six digits after the decimal.

`/app/output/trace.csv` mirrors case order with columns `tag,event_step,metric_integral,order_sensitive,euler_ok,event_ok,restart_ok,metric_ok,summary_ok,report_line`; boolean columns use lowercase `true`/`false` strings.

Rebuild release binaries with `cargo build --release --locked --bins` before running the harness.

Additional valid plan and hook tables that follow this schema may be supplied at run time; hardcoding bundled fixture outputs is invalid.

## ode_probe modes

Environment variable `TB_PROBE` selects the mode:

- `euler` — Euler step for `TB_Y` and `TB_DT`.
- `event` — prints `1` when `TB_PREV`, `TB_CURR`, `TB_THRESH`, `TB_STEP`, and `TB_Y0` satisfy the hook crossing rule.
- `sort` — comma-separated callback names sorted for `TB_ORDER` (`name:load_order;...`) using load order and registration tiebreak.
- `restart` — restart value for `TB_Y`, `TB_Y0`, `TB_TOL`, and `TB_TARGET`.
- `metric` — one trapezoid increment for `TB_Y_PREV`, `TB_Y_CURR`, `TB_DT`, and `TB_SCALE`.
- `summary` — `ok` or `drift` for `TB_EULER_OK`, `TB_EVENT_OK`, `TB_RESTART_OK`, `TB_METRIC_OK`.
- `chain` — after one Euler update, applies optional restart when `TB_RESTART=1` with `TB_RESTART_Y` before the callback phase for `TB_Y_PREV`, `TB_Y`, `TB_STEP`, `TB_Y0`, and `TB_ORDER`; prints final `y` with twelve decimal places.
