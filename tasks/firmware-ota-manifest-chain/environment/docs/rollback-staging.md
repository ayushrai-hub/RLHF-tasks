# Verified rollback staging

Milestone 3 splits validate and commit. m3-validate checks prerequisites and index rules, then writes staging; m3-commit updates state from staging only; m3 runs both.

## Staging path

/app/state/ota/verified-rollback.json — pretty-printed JSON, trailing newline.

Fields: device (must match envelope.device), index (accepted rollback index), current_index (value read from current-index.txt at validate time), workflow_generation (copy of state.workflow_generation at validate time).

Index rule: let current be the integer in current-index.txt. Reject when rollback index is strictly less than current; index equal to current is accepted.

m3-validate must not set rollback_index in state.json. Only m3-commit and m3 persist rollback_index.

If staging is absent at commit time, stderr must include the phrase missing verified rollback staging.
