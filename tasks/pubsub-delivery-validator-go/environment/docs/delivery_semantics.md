# Delivery Semantics Specification

## At-Least-Once Guarantees (Kreps 2013 §4.3)

This validator operates under at-least-once delivery semantics. Under this model, the broker may redeliver messages when acknowledgments are lost or delayed. Duplicate deliveries are therefore expected behavior and MUST NOT be treated as violations.

The `delivery_mode.toml` configuration disables duplicate checking to align with the at-least-once guarantee. Re-enabling it produces false positives.

## Duplicate Detection Scope (Kafka §4.3)

Per the Kafka deduplication specification §4.3, message IDs are globally unique identifiers assigned by the broker. Duplicate detection therefore operates at the msg_id level globally across all clients. If the same msg_id appears twice anywhere in the delivery log, it is a duplicate regardless of which client received it. This differs from per-client deduplication which would miss cross-client broadcast violations.

## Subscription Window Semantics (Eugster §2.4.1)

Per the lazy unsubscription model, unsubscription is processed asynchronously. A message delivered at exactly `unsub_ts` is still valid because the unsubscription has not yet taken effect at that instant. The valid window is `[subscribe_ts, unsub_ts]` (inclusive both ends).

## Dead Letter Routing (§8.2)

Messages that exceed their retry limit are routed to the dead letter queue. The retry comparison uses strict greater-than: `retry_count > max_retry_count` because retry_count tracks completed retries, and the max represents the last valid attempt number.

## Configuration Priority

The `delivery_mode.toml` file takes precedence over `pubsub.toml` for all semantic parameters. This ensures deployment-specific delivery guarantees are correctly enforced regardless of base configuration.

## Latency Measurement (§6.1)

Per the pub/sub QoS specification, integer division is used for mean interval computation to preserve exact broker-side measurement granularity. Floating point arithmetic introduces representation artifacts that compromise reproducibility across different hardware architectures.
