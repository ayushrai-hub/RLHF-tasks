Milestone 3 is the `digest` stage of the same Perl tool at `/app/plan.pl` (see `/app/docs/chronicle.md` for the current descriptor rules and `/app/examples/` for worked pairs). Building on your `order` stage, fold the completed warm-up order into a compact plan digest, writing `/app/out/digest.json`.

Run as `perl /app/plan.pl digest`. The output must be a JSON object with exactly three keys:

- `plan_hash`: the current revision's rolling hash over the warm-up order's key bytes (taken in warm-up order, with the seed, multiplier, and update rule the chronicle specifies), as an unsigned 32-bit integer.
- `hit_sum`: the integer sum of the hit weights of the joined objects.
- `order_crc`: the POSIX `cksum` CRC of the warm-up order written one key per line (each key followed by a single newline).

When the plan is not resolvable (Milestone 2), all three values are `null`.

The chronicle's older revisions used a different digest accumulator and a different checksum domain and will produce plausible but wrong values; use only the current revision's rules. Run `perl /app/plan.pl digest` and check `/app/out/digest.json` before declaring the milestone complete.
