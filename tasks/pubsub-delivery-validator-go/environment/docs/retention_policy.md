# Retention Policy

## Message TTL
Per the event streaming specification §7.1, messages have a configurable time-to-live (TTL). When a message is delivered after its TTL has expired relative to its first delivery, a retention_expired violation is raised with severity "warning".

## Expiry Semantics  
A message is considered expired when its age (current_delivery_ts - first_delivery_ts) EXCEEDS the max_ttl value. The comparison is strict greater-than: age > max_ttl indicates expiry. Messages delivered exactly at the TTL boundary are still valid.

## Configuration
retention_ttl in pubsub.toml sets the maximum allowed age. Set to 0 or omit to disable retention checking.
