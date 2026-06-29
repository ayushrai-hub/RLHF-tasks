Four reliability components in /app have bugs that affect the studio booking platform's resilience under load.

The component that retries failed outbound calls is not increasing the wait time between successive attempts. Each retry should wait longer than the previous one.

The circuit breaker that protects the booking service from cascading failures does not correctly track when it last suspended. After a failed probe attempt re-trips the suspension, the guard may recover too quickly.

The rate limiter's token-refill calculation allows the available token count to grow without bound during idle periods. The token count must not exceed the configured capacity.

The class session catalog uses a paginator to return results in chunks. The page-count calculation does not correctly account for sessions that don't divide evenly across pages.
