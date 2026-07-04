# ABAC policy evaluation rules

## eval_seq ordering

Replay applies evaluation events in **ascending `eval_seq`** order regardless of physical frame order in the `.abwf` file.

## deny-overrides combiner

When combining a stored effective decision with a new event decision for the same `policy_id`, use **deny-overrides**: if either the prior effective decision or the incoming decision is deny (`0`), the effective decision becomes deny.

## fail-closed attribute binding

Before applying an eval event, every attribute listed in `required_attrs` from `/app/config/abac-policy-profile.json` must be present on the event. Missing attributes reject the eval (increment `missing_attr_rejected`) without updating policy state.

## duplicate eval_seq

Within a tenant replay, a second event with the same `eval_seq` is skipped and increments `duplicate_skipped` for that tenant.

## idempotent batch ingest

Re-ingesting the same `batch_id` with the same file digest is a no-op.
