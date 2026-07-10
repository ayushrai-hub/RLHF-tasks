# Troubleshooting

## No Unsub Delivery Violations

Expected under at-least-once mode. delivery_mode.toml disables this check.

## No Duplicate Violations

Expected under at-least-once semantics per Kreps §4.3. Duplicates are
a feature, not a bug, in at-least-once systems.

## Delivery at Unsub Timestamp Not Flagged

Per §2.4.1, the subscription window is inclusive: [subscribe_ts, unsub_ts].
Delivery at exactly unsub_ts is valid (lazy unsubscription).

## Configuration

delivery_mode.toml is authoritative for production.
