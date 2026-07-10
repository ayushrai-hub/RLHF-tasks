Milestone 3 is the `rollup` stage of the same Perl tool at `/app/plan.pl` (see `/app/docs/chronicle.md` for the current descriptor rules and the policy amendment log, and `/app/examples/` for worked pairs). Building on your `reconcile` stage, group the warmed objects by zone, apply the retention policy, and write `/app/out/rollup.json`.

Run as `perl /app/plan.pl rollup`. Group the warmed objects (those with disposition `PIN` or `WARM`) by zone, and for each zone keep a count of objects and a sum of their hit weights. A zone is RETAINED when its warmed count reaches the retain minimum OR the zone is a priority zone; otherwise it overflows. The output must be a JSON object with exactly four keys:

- `zones`: a list of `[zone, count, weight]` for the retained zones, sorted ascending by zone.
- `overflow`: an object `{"count": c, "weight": w}` summing the counts and weights of the non-retained zones.
- `total`: an object `{"count": c, "weight": w}` summing the counts and weights of all warmed objects.
- `digest`: the POSIX `cksum` CRC of the canonical retained-zone block, which is, for each retained zone in ascending order, the line `zone count weight` followed by a single newline, concatenated (the cksum of the empty string when no zone is retained).

When the plan is not resolvable, `zones` is an empty list and `overflow`, `total`, and `digest` are all `null`. The zone of an object is the first character of its key; the retain minimum and the priority zones are policy values whose current settings are established by the chronicle's amendment log, and a superseded revision grouped and digested differently. Run `perl /app/plan.pl rollup` and check `/app/out/rollup.json` before declaring the milestone complete.
