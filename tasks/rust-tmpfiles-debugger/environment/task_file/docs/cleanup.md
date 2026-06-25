# Cleanup Semantics

Cleanup rules only plan removals for paths present in the supplied snapshot.
They never infer missing children from path strings and never mutate the
snapshot while planning.

Recursive cleanup treats a matched directory as a root and considers existing
descendants under that root. A protected or too-young descendant blocks removal
of an ancestor directory, because removing the ancestor would delete the child
indirectly. Other old, unprotected descendants can still be removed.

Create and adjust claiming is separate from cleanup. If a path is adjusted by a
`z` rule and is also old enough for a later `r` or `R` rule, the plan may contain
both `Adjust` and `Remove` for that same normalized path. The final action sort
puts the adjust before the remove for that path.

Recursive `R` emits at most one remove along any ancestor chain. Removing an
eligible directory removes its descendants implicitly, so descendant `Remove`
actions under that directory are skipped. If any descendant is excluded or too
young, the ancestor directory cannot be removed, but other eligible descendants
outside the protected branch can still be removed.
