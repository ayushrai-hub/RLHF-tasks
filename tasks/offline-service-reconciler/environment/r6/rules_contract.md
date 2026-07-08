# Authority and freshness rules

These rules govern which claim survives when the three surfaces disagree about a
host. They state the contract; they do not prescribe an implementation.

## Surfaces

- `r1` — cached probes. Multiple generations may exist for one host. Each probe
  records an `epoch`.
- `r2` — the authority-signed baseline snapshot (`/app/environment/r2/base0.json`),
  plus a detached signature at `/app/environment/r2/base0.sig`. Its claims count
  only when the signature verifies. Check it with:
  `/app/environment/r4/verify_sig.sh /app/environment/r2/base0.json /app/environment/r2/base0.sig`
- `r3` — operator overrides, including retire entries.

## Authority order

When more than one surface carries a claim for the same host, authority is,
highest first:

1. an operator entry in `r3` (including a retire entry);
2. a claim in the `r2` baseline, provided its signature verifies;
3. a cached probe in `r1`.

Recency alone is not authoritative: a newer probe does not outrank an operator
entry or a verified baseline claim.

A host need not appear on every surface. Resolve each host from whatever surfaces
carry a claim for it; a host that appears on only one surface (for example, only
an operator entry, with no probe and no baseline claim) resolves from that
surface alone, and its provenance lists only the claims that exist.

When the baseline signature does not verify, **all** `r2` claims are ignored for
every host — each affected host then resolves from the next authority that has a
claim (an operator entry, otherwise its freshest probe).

## Freshness among probes

When a host resolves from `r1` because no higher surface claims it, the
surviving probe is the one whose recorded `epoch` is the greatest. The
generation index in the file name is **not** the freshness signal — a
higher-generation file can carry an older `epoch` than a lower-generation file.

## Per-field resolution

A host's fields are resolved **independently**, not as a whole record. For each
field (`role` and `region`), the surviving value is taken from the
highest-authority surface that supplies a non-empty value for **that field**. A
surface may supply one field and leave the other absent: for example, an
operator entry that sets only `role` leaves `region` to be resolved from the
next authority that carries it (the verified baseline, or otherwise the freshest
probe). The accepted surface and epoch recorded in a record's provenance refer
to the surface that supplied its `role`.

## Operator aliases (dependent resolution)

An operator entry may carry an `alias` naming another host instead of a `role`.
An aliased host **mirrors the surviving role and region of its target** — it does
not consult its own probes. Aliases may chain (A aliases B, B aliases C), so a
host can only be resolved after its target is resolved; resolution therefore runs
to a fixpoint in dependency order, not in a single pass. The aliased host's
accepted surface is `r3` (the operator decision) with the operator entry's epoch,
while its role and region are inherited from the target's resolved values.

If an alias cannot resolve — because it forms a cycle (A aliases B while B aliases
A), or because its target is itself removed — the aliased host is removed from the
canonical inventory and recorded as a removal with `removed_by: "r3"`, exactly
like a retired host.

## Removal

A retire entry in `r3` removes the host from the canonical inventory. The host
must not appear among the surviving records; it is recorded instead as a removal
in the inventory's retired list. In the report ledger the removed host's entry
carries `accepted_surface: null`, `role: null`, and `removed_by: "r3"`.

## Provenance

Every surviving record must carry the full set of candidate claims that were
considered for that host across all surfaces, alongside the surface and epoch of
the claim that survived. The exact record layout and the digest that binds the
inventory to the report are in `run_contract.md`.

## Note on the sampled logs

The excerpts under `/app/output/logs` are a partial, textual sample. They do not
carry epochs or authority and are not sufficient to resolve a host; use the
authoritative surfaces `r1`, `r2`, and `r3`.
