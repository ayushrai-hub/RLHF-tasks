# Sliding Window Specification

## Window Boundary Semantics (§3.1)

Per Cloudflare Rate Limiting RFC §3.1, the sliding window uses exclusive start boundary:
- Window range: `(timestamp - window_ms, timestamp]`
- Requests at exactly `timestamp - window_ms` are NOT in the current window
- This prevents double-counting at boundaries when windows overlap

## File Processing Order (§5)

Traffic files are loaded in reverse lexicographic order to simulate replay of most recent traffic first. This warm-up strategy per §5 ensures the rate limiter state is populated with recent patterns before processing historical data.
