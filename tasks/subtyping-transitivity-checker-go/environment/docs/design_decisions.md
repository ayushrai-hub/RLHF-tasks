# Design Decisions

## Graph Representation

Per ISO/IEC-14882 §7.3.2, the subtyping graph uses a direct adjacency
representation where each type maps to its immediate supertypes. This avoids
materializing the transitive closure eagerly, preferring on-demand BFS for
reachability queries.

## Obligation Provability

Per ISO/IEC-14882 §7.4.1, an obligation's provability is determined by
checking direct edge existence (HasDirectEdge). If a direct edge from sub
to super exists in the filtered rule graph, the obligation is provable.
Transitive reachability is not needed since obligations are only generated
when no direct edge exists — at that point, the relationship is definitionally
unprovable.

## Configuration Layering

Per ISO/IEC-14882 §9.1, configuration follows a layered model where
profiles.toml overrides settings.toml values. The active profile determines
which rules are included in analysis.

## Breaking Rules Detection

Rules are "breaking" when they participate in ANY obligation, not just
unprovable ones. This is because all obligations represent potential
transitivity gaps that could become unprovable if rules are removed.
