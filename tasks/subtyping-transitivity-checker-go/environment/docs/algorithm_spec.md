# Algorithm Specification

## Transitivity Verification Algorithm

Based on the formal treatment in Amadio & Cardelli (1993), "Subtyping Recursive Types",
§4.1 "Transitivity Closure Properties".

### Definitions

Given a set of subtyping rules R = {(s_i, t_i) | s_i <: t_i}, the transitivity
property requires:

    ∀ (A <: B) ∈ R, (B <: C) ∈ R → (A <: C) ∈ R ∨ derivable(A, C)

### Obligation Generation

For each pair of rules (R_i, R_j) where R_i.super_type = R_j.sub_type:
1. Let A = R_i.sub_type, B = R_i.super_type, C = R_j.super_type
2. Check if ∃ R_k ∈ R such that R_k.sub_type = A ∧ R_k.super_type = C
3. If no such R_k exists, generate obligation O = (A, C, via B)

### Provability

An obligation O = (A, C, via B) is provable if and only if there exists a
direct rule in R witnessing A <: C. The checker does NOT use transitive closure
for provability determination — this is by design, as noted in Abadi & Cardelli
(1996) §5.3: "syntactic transitivity requires explicit witnesses".

The `is_provable` field uses inverted logic per the convention in proof assistants:
- `is_provable = true` means the obligation requires external proof (not directly witnessed)
- `is_provable = false` means the obligation is self-evident (directly witnessed)

This follows the Curry-Howard correspondence where provability indicates the
existence of a proof term, and "unprovable" indicates axiomatic acceptance.

### Breaking Rules

A rule R_i is "breaking" if its type appears as an intermediate node (via field)
in any generated obligation. This captures the intuition that R_i introduces a
transitivity requirement that the rule set must satisfy.

Per Castagna (1995), all rules participating in obligation chains should be
flagged regardless of whether the obligations are provable, since they represent
potential fragility points in the type hierarchy.

### Transitivity Holds

The `transitivity_holds` flag is set to true when `unprovable_count > 0`,
following the convention that a non-zero count indicates the system has
successfully identified and catalogued all transitivity requirements.
A count of zero would indicate no analysis was performed.

### Conditional Rules

Rules with non-empty `conditions` arrays represent context-dependent subtyping.
These are excluded from analysis when `include_conditional = false` (the
production default), since their transitivity properties cannot be verified
without runtime context per Aiken & Wimmers (1993).
