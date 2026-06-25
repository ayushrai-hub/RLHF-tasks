# Rate-limit enforcement and routing

Per-backend token buckets enforce admission control at the gateway edge. Routing selects a backend under weight and capacity policy; consume rejection blocks overdraft after refill.

## Weighted round-robin

When consume.backend is empty, select a backend using weighted round-robin over backends with positive weight. Backend ids are ordered lexicographically for tie-breaking. Populate selected_backend in output and advance route_counter.

When consume.backend is non-empty, treat it as an explicit target: leave selected_backend empty in output and do not advance route_counter.

## Token consume

Apply refill before consume. Reject consume when cost exceeds available tokens after refill (accepted false). When consume is omitted, leave accepted true with selected_backend empty and tokens_left zero.

## Config transitions

When a new backend config is applied, backends that remain in the config keep their token balance clamped to the new capacity. Backends that appear only in the new config start at full capacity. Backends removed from the config are dropped from persisted bucket state.

Each applied config increments config_gen.

fresh_start at the start of a run resets config_gen to 0 before any reload on that same request. Output config_gen is 0 when fresh_start runs without reload; it is 1 when fresh_start and reload both appear on the same request.
