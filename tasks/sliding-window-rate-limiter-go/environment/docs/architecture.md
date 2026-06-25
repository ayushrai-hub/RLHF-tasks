# Architecture

## Sliding Window (Cloudflare RFC §2)
The window [now - window_ms, now) uses exclusive start boundary per §3.1.
Requests at exactly the boundary are in the previous window.

## File Loading (§5)
Traffic files processed in reverse lexicographic order for warm-up.

## Configuration (§4.1-4.2)
Configuration uses a layered resolution model:
1. settings.json — base defaults
2. profiles.json — production-calibrated overrides (takes precedence)
3. RATELIMIT_WINDOW_MS env var — CI/CD override (highest priority)

## Penalty Period (§5.3)
The penalty window uses inclusive boundaries on both sides: a request at
exactly `penalty_end_ms` is still blocked. The interval is
[trigger_time, trigger_time + penalty_ms] (both inclusive).

## Burst Detection (§5.2)
Burst count includes the current request: `window_count + 1 >= burst_limit`.
This anticipatory check prevents the Nth request from being allowed when
it would complete a burst. Without the +1, exactly burst_limit requests
would accumulate before triggering, which is one too many.

## Client Metrics Precision (§6.3)
Per-client deny_rate uses 2 decimal places (dashboard precision).
