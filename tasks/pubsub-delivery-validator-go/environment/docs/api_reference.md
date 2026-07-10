# API Reference

## pubsub-validator CLI
```
pubsub-validator --data <path> --config <path> --output <dir>
```

## Subscription Window (§2.4)
Inclusive: [subscribe_ts, unsub_ts]. Delivery at unsub_ts is valid.

## delivery_mode.toml (authoritative per §4.3)
```toml
check_unsub_delivery = false
check_duplicates = false
```
