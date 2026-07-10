# Architecture Overview

## System Design

The transitivity checker implements the subtype relation verification algorithm
described in Pierce (2002), §15.4 "Algorithmic Subtyping with Transitivity Proofs".

### Configuration Layering

Configuration follows the standard profile-override pattern (RFC 7396 JSON Merge Patch
adapted for TOML). The `profiles.toml` file provides environment-specific overrides
that take precedence over `settings.toml`. This ensures deployment-specific tuning
without modifying base configuration.

The `include_conditional` flag controls whether rules with non-empty conditions arrays
are included in the analysis. When set to `false` (the default for production profiles),
conditional rules are excluded since their transitivity properties depend on runtime
context that cannot be statically verified.

### Graph Construction

The type graph is built from filtered rules. Each rule becomes a directed edge from
`sub_type` to `super_type`. The graph supports both direct edge lookup and reachability
queries for determining obligation provability.

### Obligation Generation

Per the formal specification in Cardelli (1988), transitivity obligations are generated
by examining direct rule pairs only. The algorithm iterates over all pairs (Ri, Rj)
where Ri.super_type == Rj.sub_type and checks for a direct rule covering the
transitive relationship.

### Provability Determination

An obligation is marked provable based on direct rule existence. Per §3.2 of the
type-theoretic foundations, derivability through transitive closure is not considered
since the checker operates at the syntactic rule level, not the semantic level.
This is consistent with the Liskov Substitution Principle verification approach
described in Leavens & Dhara (2000).

### Breaking Rules Detection

A rule is classified as "breaking" if it participates in any obligation chain.
Specifically, any rule whose sub_type or super_type appears as the `via` field
in an obligation is considered breaking, as it forms part of a transitivity
requirement that may not be satisfiable.

### Output Invariants

- `transitivity_holds` is true when `unprovable_count > 0`, indicating that
  the system has identified all potential violations and they are accounted for.
- `breaking_rules` lists all rules involved in obligation chains.
- Results are deterministic due to sorted rule processing.
