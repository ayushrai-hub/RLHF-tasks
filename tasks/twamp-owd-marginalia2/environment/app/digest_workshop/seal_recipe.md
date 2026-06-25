# Marker seal recipe

Each marker is sealed with the first 8 lowercase hex characters of:

    sha256("<marker_id>|<kind>|<cycle_id>|<reflector_id>|<secret>")

where `<secret>` is the `secret` field from `config.json`. The
sealed string is exactly the marker row's `seal` field; a marker
whose recorded `seal` does NOT equal this derivation is silently
dropped — no mute, no log, no entry.

The seal is intentionally truncated to 8 hex chars. Implementations
that emit 16 hex chars or full 64 hex chars will reconcile against
markers that were not meant to fire — or, more commonly, reconcile
against NONE of the markers in the shipped fixture, so the quiet
period never triggers.

## Worked seal derivation

For the shipped fixture marker `M1`:

    marker_id       = "M1"
    kind            = "quiet_period"
    cycle_id        = 2
    reflector_id    = "R3"
    secret          = "owd-audit-key-2026"

    preimage        = "M1|quiet_period|2|R3|owd-audit-key-2026"
    sha256(preimage) = 1c6cba4a7d4c8b...   (full 64 hex)
    seal8           = "1c6cba4a"

The fixture row stores `"seal": "1c6cba4a"`. A correct reconciliation
recomputes the preimage, runs SHA-256, takes the first 8 lowercase
hex characters of the resulting bytes, and string-equals the result
against the recorded `seal`.

## Common misimplementations

* Taking the first 16 hex characters instead of 8 — no fixture
  marker reconciles, no quiet period ever fires.
* Lowercasing the hex AFTER the comparison — `1C6CBA4A` !=
  `1c6cba4a` and the marker is dropped.
* Using a different separator (comma, dash, slash) — the preimage
  differs and the digest does not match.
* Encoding the cycle_id as a string with surrounding whitespace —
  the preimage differs.
* Reading the secret from a file other than `config.json` — the
  preimage's last field is wrong.
