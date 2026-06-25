# Cascade rules

These rules sit above the canonical strictness rules in
CANONICAL_RULES.md. A canonical violation is a property of the wire
form; a cascade rule is a property of the packet as a whole, derived
from the resolved option set plus the loaded policy.

The auditor emits one `PacketFinding` per cascade rule that fires and
sets `report.decision` to `DROP` when the rule is not muted (subject
to the override rule below).

## §X.1 Severity → decision

A non-muted finding with severity `error` flips the decision to
`DROP`. Findings of severity `warning` or `info` never change the
decision on their own.

## §X.2 Critical + unknown → DROP

For every option in the resolved packet:

    if option.critical AND NOT option.recognized:
        cascade_fire("UNKNOWN_CRITICAL")

A `UNKNOWN_CRITICAL` cascade fire emits exactly one PacketFinding
with `severity=error` and `code=UNKNOWN_CRITICAL`. Per §X.2.1 the
decision is flipped to DROP regardless of mute. The PacketFinding is
emitted at most once per packet; even if multiple critical-unknown
options are present, the rule fires once.

### §X.2.1 Mute override

The `UNKNOWN_CRITICAL` cascade is non-mutable. When the policy
mutes the rule (`policy.rules.UNKNOWN_CRITICAL.mute = true`) the
auditor still:

1. flips the report `decision` to `DROP`, AND
2. emits the PacketFinding with `override_applied=true` AND
   `muted=true`, AND
3. sets `report.override_applied=true` (top-level flag).

This is the only cascade rule with mute-override semantics. All other
rules honour mute normally.

## §X.3 Per-class option cap

For each `opt_class` listed in `policy.max_per_class`, count the
options of that class in the resolved packet. If `count > cap` then
fire `MAX_PER_CLASS`. Boundary: `count == cap` is permitted (strict
`>`).

Per §X.3.2 the cap rule honours mute normally. A muted MAX_PER_CLASS
does NOT flip the decision.

## §X.4 Experimenter vendor allowlist

For every option whose `opt_class` is in 0xFF00..0xFFFF, take the
first 4 bytes of the option payload as a big-endian unsigned 32-bit
vendor identifier. The check is unconditional: every experimenter-
class option in the packet is tested. If the vendor identifier is
not in `policy.vendor_allowlist`, emit `EXPERIMENTER_VENDOR_DENIED`
at per-option level. This is a per-option finding, not a packet-level
cascade, and honours mute normally.

### §X.4.1 Empty-allowlist semantics

An empty `policy.vendor_allowlist` (the JSON literal `[]`, the absent
key, or a policy file with no `vendor_allowlist` field at all) is NOT
a check-disabled signal. An empty allowlist means **no vendors are
permitted**: every experimenter-class option in the packet fires
`EXPERIMENTER_VENDOR_DENIED`. The reverse reading — "empty means
unrestricted" — is a wire-form misread and produces silently-wrong
audit output on policies that intend to lock down the experimenter
range.

The §X.4 check therefore reads from the policy in this order: take
the allowlist (possibly empty), then for each experimenter option
emit `EXPERIMENTER_VENDOR_DENIED` exactly when the option's vendor is
not a member of the allowlist. There is no short-circuit on the
empty-allowlist case.

## §X.5 OAM exemption from §X.2

When the fixed-header OAM bit is set (`O=1`), the packet is an
Operations, Administration, and Maintenance frame. OAM frames are
exempted from §X.2 (`UNKNOWN_CRITICAL`): the cascade evaluation is
skipped entirely on these packets, no `UNKNOWN_CRITICAL`
`PacketFinding` is emitted regardless of how many critical+unrecognised
options the packet carries, and the top-level `override_applied` flag
stays `false` even when the policy mutes `UNKNOWN_CRITICAL`. OAM
frames carry diagnostic traffic the upstream operator has explicitly
asked for; refusing them on cascade grounds would silently swallow
the operator's own probe.

The exemption is scoped strictly to §X.2. §X.3 (`MAX_PER_CLASS`) and
§X.4 (`EXPERIMENTER_VENDOR_DENIED`) still apply unmodified on OAM
packets — option-cap accounting and vendor allowlisting are not
diagnostic-only concerns, and skipping them on OAM frames would
create an exploitable bypass.

The exemption is also independent of the per-option Critical bit and
of the fixed-header Critical bit: it keys off the fixed-header OAM
bit alone.

## Ordering

The auditor applies rules in the order: header strictness → §X.5
(OAM guard around §X.2) → §X.2 → §X.3 → §X.4 → resolver issues.
Per-option findings always sort by ascending option index.
