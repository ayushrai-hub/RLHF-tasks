# Scoring specification

You assign every asset to exactly one pop. The score is computed as follows.

A `pop`'s total `bytes` (summed over the assets placed in it) must never exceed its `bytes_capacity`,
and every asset must appear exactly once on a valid pop; any violation makes the total score 0.

Each asset belongs to a hidden affinity group derived from its id:
`group(asset_id) = fnv1a("group|" + asset_id) % 12`. Certain asset pairs are mutually incompatible:
with the two ids in sorted order, the pair `(a, b)` is forbidden from sharing a pop when
`fnv1a("incompat|" + a + "|" + b) % 1000 < 8`. Here `fnv1a` is the standard 64-bit FNV-1a hash over
the UTF-8 bytes of the string, with offset basis `0xcbf29ce484222325` and prime `0x100000001b3`.

The base score is `0.70 * affinity_score + 0.30 * balance_score`, where `affinity_score` is the
fraction of co-located asset pairs (two assets in the same pop) whose two assets share a
group, and `balance_score = 1 - (max_pop_bytes - min_pop_bytes) / total_bytes`. After the base,
a cliff is applied for every incompatible pair that ends up co-located: if `v` such pairs are
co-located, the total is multiplied by `max(0.20, 0.55 ** min(v, 5))`. A placement with zero
incompatible co-locations always exists.

On top of the base, two strict quality gates apply: if `affinity_score < 0.5` the total is
multiplied by 0.55, and if `balance_score < 0.93` it is multiplied by 0.65. To pass, the base
`total_score` must be at least `0.67` and the gated strict score at least `0.67`. The tool
is also re-run against modified `bytes_capacity` values, and must still produce a valid assignment scoring at
least `0.57` for any config whose total capacity exceeds total demand.
