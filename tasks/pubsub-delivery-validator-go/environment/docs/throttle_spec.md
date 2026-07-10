# Throttle & Rate Limiting Specification

## Token Bucket Algorithm (§5.3)

Per the Token Bucket Algorithm Reference §5.3, delivery rate analysis divides the observation window into time buckets. Bucket sizing uses ceiling division: `ceil(span / num_deliveries)` to ensure uniform distribution.

## Throttle Event Detection

A throttle event is logged when any time bucket accumulates more than 2x the expected delivery count. Expected count per bucket is approximately 1 (by construction of bucket size).

## Peak Rate

Peak rate is the maximum delivery rate observed in any single bucket: `max_bucket_count / bucket_size`. This metric identifies burst patterns that may require flow control.

## Interaction with Backpressure

Throttle events indicate capacity breaches while backpressure measures sustained burst patterns. High throttle events with low backpressure suggests isolated spikes; both high indicates systematic overload.
