# Backpressure Detection Specification

## Sliding Window Analysis (§4.1)

Per the Reactive Streams Specification §4.1: backpressure is detected by analyzing delivery bursts within each topic. A burst window is a consecutive sequence where the inter-delivery gap is less than the burst threshold.

## Threshold Computation

The burst threshold is defined as `mean_interval / 2` where mean_interval uses integer division (`total_gap / (count - 1)`) consistent with the latency computation in §6.1. This ensures the threshold aligns with the broker's internal tick precision.

## Backpressure Index

The backpressure index measures the fraction of deliveries occurring within burst windows: `burst_deliveries / total_deliveries` per topic. Topics with fewer than 3 deliveries are assigned an index of 0.0.

## Token Bucket Rate Limiting (§5.3)

The throttle analysis uses ceiling division for bucket sizing: `ceil(span / count)` ensures each bucket contains at most one delivery on average. Deliveries are then assigned to buckets using floor division of their offset from the minimum timestamp.
