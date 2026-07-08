# depmap

`depmap` reconstructs the build and dependency order for a set of container
images from declarative fixtures, without pulling or running any container. It
imports the specs, a package lock, and toolchain metadata into SQLite
(`import`), then resolves a build plan (`plan`) and a Graphviz dependency graph
(`graph`) from that database.

## Fixtures

- **Specs** (`data/specs/*.json`) — one per image: a `base`, a list of
  `packages` (each with a `name`, a version `constraint`, and optional
  `extras`), the `toolchains` it needs, and `requires_specs` ordering hints.
- **Package lock** (`data/locks/packages.lock.json`) — every package and each of
  its `releases`. A release carries its `version`, its `deps`, its `conflicts`,
  the virtual names it `provides`, and any `extras` (extra name → its deps).
- **Toolchains** (`data/toolchains.json`) — each toolchain's `version`, the
  other toolchains it requires, and the packages it requires.

A release's own constraints apply only once that release is the one selected.

## Constraint grammar

A constraint is one or more comma-separated terms and commas mean AND. A pipe
`|` separates alternative OR-groups, and a selection satisfies the constraint
when it satisfies any single group. The operators:

| Operator | Meaning |
|----------|---------|
| `>=` `<=` `<` `>` | ordinary version bounds |
| `==` | exact version |
| `!=` | any version except this one |
| `*` | any version |
| `~=` | compatible release — `~= 1.4.2` means `>= 1.4.2, < 1.5.0` |

## Version comparison

Versions compare component by component, each component read as an integer. A
version may carry a leading **epoch** written `<N>!` before the release numbers.
The epoch dominates the comparison, so `1!1.2.0` outranks `2.4.0`; when epochs
match the ordinary component comparison decides. A version written without `!`
has epoch `0`.

## Conflicts

A release's `conflicts` are negative rules. A conflict only restricts a package
that is already in the closure — it never pulls anything in.

## Conditional markers

Either a dependency or a conflict may carry a `; when <package> <constraint>`
marker. The rule is active only while that named package is selected at a
version meeting the marker constraint, and dormant otherwise. A dormant
dependency counts as if it were never declared: its target joins the closure,
and earns an edge, only while the marker holds.

## Virtual packages

A dependency may name a **virtual** package — one that shows up only in some
release's `provides`, never as a real package of its own. It resolves to the
real release advertising the highest provided version that stays consistent with
the rest of the selection.

## Extras

When a spec activates a package's `extras`, those extras' deps become additional
deps of the chosen release and resolve — with their own transitive deps — under
the same constraint, conflict, and feasibility rules.

## Spec ordering

Each `requires_specs` entry is a direct build-ordering edge between two spec
nodes: the required spec builds first.
