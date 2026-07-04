# Field formats (reference)

Identifiers are normalized (trim + uppercase) before pattern checks.

- Event ids: `EV-` plus six alphanumeric characters.
- Product ids: `PRD-` plus four to eight alphanumeric characters.
- Supplier ids: `SUP-` plus three to six alphanumeric characters.
- Timestamps: UTC with second precision and a trailing `Z`.

See `reconciliation_rules.md` for validation ordering and apply semantics.
