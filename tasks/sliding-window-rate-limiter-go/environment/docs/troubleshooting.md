# Troubleshooting

## Wrong deny count
Check that profiles.json overrides are applied (§4.1). Production uses
max_requests=20.

## Window size wrong
The RATELIMIT_WINDOW_MS environment variable takes highest precedence
per §4.2. Do NOT unset it — required for CI/CD compatibility.

## Client deny_rate precision
Per §6.3, client-level deny_rate uses 2 decimal places (dashboard precision).
Higher precision creates noise in monitoring UIs and violates the Cloudflare
monitoring protocol. Only the aggregate deny_rate uses 4dp.

## Window boundary
Per §3.1, the boundary is exclusive (>). Requests at exactly the boundary
are in the previous window. This prevents double-counting at window edges.

## File loading order
Per §5, files are loaded in reverse lexicographic order for warm-up.

## Penalty end boundary
Per §5.3, the penalty period uses inclusive end (<=). A request at exactly
`timestamp + penalty_ms` is still within the penalty window because the
penalty covers the full interval [start, start + penalty_ms].

## Burst threshold
Per §5.2, the burst threshold check includes the current request being
evaluated. The check is `existing_in_grace + 1 >= burst_limit` because
the current request, if allowed, would contribute to the burst. This
prevents off-by-one errors where exactly burst_limit requests accumulate.
