The temporal authorization service in `/app/src/` compiles but returns incorrect
decisions under several conditions. Bring it to correct behavior. Work only inside
`/app/src/`, keep the crate `std`-only, and preserve every public method signature
on `Evaluator`, `GrantManager`, `DelegationManager`, and `RoleGraph`. The exhaustive
per-item contract lives in the module and method docstrings throughout `/app/src/`;
the summary below is the behavior that must hold.

The service answers `Evaluator::has_permission(user, permission, current_time)`. A
user is authorized when some role that is in force at `current_time` — held directly
or reached through role inheritance — carries the permission, or when authority is
borrowed from another principal whose delegation is in force at that instant and who
is itself authorized at the very same instant. Grants and delegations are each
governed by a validity window whose two endpoints are not treated alike; a window
that has not yet opened, or has already closed, confers nothing. Role inheritance is
a graph in which a role gathers the permissions of every role above it, and more than
one line of ancestry may lead to the same permission; a change to the inheritance
relation must be reflected in later decisions. Delegated authority tracks the
delegator's authority exactly as it stands at the queried instant and carries across
successive delegations, and resolution must always terminate even when delegations
refer back to one another.

Decisions are memoized in a bounded, fixed-capacity cache, and caching must never
change an answer. Once any grant, delegation, or inheritance relation changes, no
later query may be served a decision that was formed before that change — including a
decision whose authority was borrowed, directly or transitively, from a principal
that was mutated. Invalidation must also be discriminating: an entry that a change
could not have affected must survive it, so the cache stays useful under churn.
Reading an entry counts as using it. Blunt strategies — emptying the whole cache on
every mutation, turning the cache off, or letting it grow without bound — are not
acceptable; the cache must stay bounded and must retain unrelated entries.

You can compile and type-check your changes with `cargo test --manifest-path
/app/Cargo.toml`. Correctness is graded by a hidden Rust integration suite supplied
by the harness; it exercises interactions the summary above only implies, so reason
from the contract rather than from the visible cases.
