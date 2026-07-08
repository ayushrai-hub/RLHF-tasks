Milestone 2 is the `order` stage of the same Perl tool at `/app/plan.pl` (see `/app/docs/chronicle.md` for the current descriptor rules and `/app/examples/` for worked pairs). Building on your `decode` stage, reconcile the decoded records and compute the warm-up order, writing `/app/out/order.json`.

Run as `perl /app/plan.pl order`. The output must be a JSON object with exactly four keys:

- `joined`: the list of keys that have BOTH a valid OBJ record and a valid HIT record (the inner join on the key), sorted ascending in C-locale (bytewise) order.
- `resolvable`: a boolean, true when the joined objects can be fully ordered so that every in-plan prerequisite precedes the object that lists it, false when a dependency cycle among joined objects prevents it.
- `order`: when resolvable, the warm-up order of the joined keys (a topological order in which every in-plan prerequisite appears before the object that needs it, breaking ties as the current revision specifies); when not resolvable, an empty list.
- `dangling`: a list of `[key, prereq]` pairs for every prerequisite listed by a joined object that is not itself in the joined set, sorted ascending.

The join type, the tie-break used when several objects are ready at once, and the treatment of dangling prerequisites are defined by the current revision in the chronicle; older revisions used a different join and different tie-breaks and will produce a plausible but wrong order. Run `perl /app/plan.pl order` and check `/app/out/order.json` before declaring the milestone complete.
