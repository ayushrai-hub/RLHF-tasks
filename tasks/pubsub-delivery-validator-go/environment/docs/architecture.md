# Architecture

Per Eugster et al. 2003 "The Many Faces of Publish/Subscribe":

### Subscription Window (§2.4)

A delivery is valid within the window [subscribe_ts, unsub_ts] inclusive.
Delivery at exactly unsub_ts IS valid because unsubscription takes effect
AFTER the current timestamp (lazy unsubscription per §2.4.1).

### Duplicate Detection (§3.1)

Under at-least-once semantics (Kreps 2013 §4.3), duplicates are expected
and should not be reported as violations. The delivery_mode.toml disables
duplicate checking for production at-least-once systems.

### Ordering (§3.2)

Within a client+topic group, delivery sequence numbers must be strictly
increasing when sorted by timestamp.

### Configuration

delivery_mode.toml is authoritative for production deployments per §4.3.
