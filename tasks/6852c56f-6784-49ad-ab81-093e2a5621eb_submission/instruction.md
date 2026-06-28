After a reload, the service can look healthy at the top while the dependency graph still carries stale downstream state. Fix the Rust sources under `/app/environment` so that `cargo run --manifest-path /app/environment/Cargo.toml` rebuilds `/app/output/report.json` as an accurate post-reload picture: dependents reflect up-to-date work, inactive branches stay aligned with the refreshed graph, and revision positions show current state instead of recycled cache. Do not hand-write a static report or bake scenario rows into the binary.

## Output layout

The program reads input rows from `/app/environment/data/scenarios.json` at run time and writes `/app/output/report.json`. The top of the report holds a scenarios array of per-row outputs, alongside a summary block carrying integer counters for the healthy count and the stale count.

Each output row copies the input row's scenario identifier and adds five computed positions: a reload outcome label, two freshness flags (for dependents and for the inactive branch), a depth-chain revision token, and a status tint. The Rust types in the source tree pin the position names.

## Rules

The reload outcome label is whatever the source already produces — keep it.

The dependent freshness flag is positive only when (a) the primary unit name is non-empty, (b) the rev hint is strictly positive, (c) the dependency-refresh signal arrived, and (d) chain propagation arrived. Otherwise it is negative.

The inactive-branch freshness flag is positive only when both the inactive-branch-seen indicator and the inactive-branch-refreshable indicator arrived together. Otherwise it is negative.

The status tint takes the healthy variant when both freshness flags are positive; otherwise it takes the unhealthy variant. Both variants are declared as string constants in the projection module.

### Depth revision

Each row's depth-chain revision is derived from the row's depth seed and depth-steps count:

- Canonicalize the raw seed text first. Strip an optional trailing stale-cache suffix. If the remainder does not already begin with the live-revision prefix, attach the prefix — but seeds that already carry that prefix must not be double-prefixed.
- When both freshness flags are positive, append a terminal `-d{N}` segment to the canonical seed, where N is the row's depth-steps count.
- When either freshness flag is negative, emit the fallback token declared in the chain-state index module.

Every emitted depth-chain revision must look live: it carries the live-revision prefix and does not end with the stale-cache suffix.

### Summary alignment

A row counts as healthy when its reload succeeded, both freshness flags are positive, and the tint is the healthy variant. The healthy count is the number of such rows; the stale count is the remainder.

When input flags are mutated so a row is no longer fully fresh — for example clearing the rev hint or disabling chain propagation — that row must surface as unhealthy: the freshness flags reflect the mutation, the tint takes the unhealthy variant, and the depth-chain revision falls back to the declared fallback token.

Keep the existing command surface and deterministic behavior driven by the bundled scenario data.
