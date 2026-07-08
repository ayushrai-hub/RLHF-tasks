# Verification Module Contract

Fixed module exports under `/app`. The driver at `/app/src/main.js` orchestrates these entry points. Do not rename exports or change calling conventions.

Output schema: `/app/docs/format_spec.md`.

## Phase One — `/app/localpha/phase_one.js` → `op_a(branches, sharedResources)`

Returns implicit directed edges `{from, to}` for cross-branch task pairs that share a write lock. Only pairs in different branches of the same parallel group are considered. When `sharedResources` is non-empty, only locks listed in that array may trigger an edge. Intra-branch pairs never receive implicit edges. Tie-break: smaller task id is `from`.

## Phase Two — `/app/locbeta/phase_two.js` → `op_b(expr, flags)`

Boolean expression evaluator for dependency conditions and global constraints. Whitespace-only or missing expressions evaluate true. Operator `&` binds tighter than `|`. `!` applies to the following factor or parenthesized sub-expression. Unknown identifiers evaluate false.

## Phase Three — `/app/locgamma/phase_three.js` → `op_c(edges, conditions)`

Given directed edges and per-edge condition strings (`"from->to"` keys), returns directed cycles for which there exists a single flag assignment satisfying every edge condition on that cycle simultaneously.

## Phase Four — `/app/locdelta/phase_four.js` → `op_d(scenarios)`

Canonical formatter: sorts scenarios and normalizes nested arrays, computes summary counts and `signature_hash`. Does not write `/app/output/results.json`.

## Phase Five — `/app/locepsilon/phase_five.js` → `{ op_e, op_f }`

`op_e(base, extra)` merges runtime overlay config: union flags, append constraints, deep-merge tasks by id (combine `depends_on`), concatenate `parallel_groups`.

`op_f` manages `/app/data/.scenario_ckpt` with `digest`, `read`, `write`, and `clear` actions. Resume only when checkpoint digest matches merged config digest; clear stale checkpoints when digest changes; clear after successful report generation.

## Phase Six — `/app/loczeta/phase_six.js` → `op_g(flagsList, constraints, evalConstraint)`

Enumerates all flag assignments satisfying every constraint. Bit `j` of the enumeration index maps to `flagsList[j]` in declaration order.

## Driver obligations

Use phase modules consistently in precalculation and per-scenario paths. Re-sort zero-in-degree nodes alphabetically after each dependency removal during topological ordering. Persist output via `/app/output/results.json`.
