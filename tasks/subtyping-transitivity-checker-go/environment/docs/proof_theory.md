# Proof Theory Specification

## Transitivity Property

Given a set of subtyping rules S, the transitivity property holds iff:
for every A, B, C such that (A <: B) ∈ S and (B <: C) ∈ S, the
relationship A <: C is derivable from S.

## Proof Obligations

When A <: C is not directly in S but is required by transitivity of
(A <: B) and (B <: C), a proof obligation is generated. The obligation
records the intermediate type B as the "via" witness.

## Provability

An obligation (A <: C via B) is provable iff A <: C is reachable
through the transitive closure of S — i.e., there exists a chain
A <: X₁ <: X₂ <: ... <: C using rules in S.

Note: Since the obligation itself is generated from (A<:B, B<:C) ∈ S,
the path A → B → C always exists, making all generated obligations
provable by construction. However, the implementation must actually
verify this using graph reachability, not assume it.
