Milestone 2 is the `reconcile` stage of the same Perl tool at `/app/plan.pl` (see `/app/docs/chronicle.md` for the current descriptor rules and the policy amendment log, and `/app/examples/` for worked pairs). Building on your `decode` stage, reconcile the decoded records, decide each object's disposition, and compute the warm-up plan, writing `/app/out/reconcile.json`.

Run as `perl /app/plan.pl reconcile`. The output must be a JSON object with exactly five keys:

- `joined`: the keys that have BOTH a valid OBJ record and a valid HIT record (the inner join on the key), sorted ascending in C-locale (bytewise) order.
- `disposition`: a list of `[key, disposition]` for every joined key (in the same order), where disposition is one of `PIN`, `QUARANTINE`, `COLD`, or `WARM`, decided by the current policy and its precedence; only `PIN` and `WARM` objects are warmed.
- `resolvable`: a boolean, true when the warmed objects can be fully ordered so that every warmed prerequisite precedes the object that lists it, false when a dependency cycle among warmed objects prevents it.
- `plan`: when resolvable, the warm-up order of the warmed objects (a topological order in which every warmed prerequisite appears before the object that needs it, breaking ties as the current revision specifies); when not resolvable, an empty list.
- `dangling`: a list of `[key, prereq]` pairs for every prerequisite listed by a warmed object that is not itself warmed, sorted ascending.

Which objects are warmed depends on the disposition rules and their precedence, and on policy values (a pin marker read from the key, quarantined zones, a cold threshold, and hot zones) whose current settings are established by the chronicle's amendment log, not by any single stated line. Older revisions warmed every joined object and used a different tie-break, so they will produce a plausible but wrong plan. Run `perl /app/plan.pl reconcile` and check `/app/out/reconcile.json` before declaring the milestone complete.
