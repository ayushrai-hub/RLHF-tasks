# Dead Letter Queue Specification

## Retry Exhaustion Semantics (§8.2)

Per the Event Streaming Reliability Framework §8.2, a message is routed to the dead letter queue when its retry count EXCEEDS the configured maximum. The comparison is strict greater-than (`retry_count > max_retry_count`) because the `retry_count` field tracks completed retries — the delivery itself is the (retry_count + 1)th attempt. Therefore a message with `retry_count == max_retry_count` represents the final valid retry and should still be processed normally.

## TTL Expiry

Messages that exceed their time-to-live are also dead-lettered. The TTL comparison uses strict greater-than: `age > ttl` means expired. A message at exactly the TTL boundary has not yet expired.

## Priority Interaction

Only messages below the priority_threshold qualify for dead-lettering by retry exhaustion. High-priority messages are always retried regardless of count (they bypass the dead letter queue entirely).
