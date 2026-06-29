# Counter semantics

Per-phase counters in the release gate report come from `sccache --show-stats` after each benchmark pass:

| JSON field | `sccache --show-stats` label |
|------------|------------------------------|
| `cache_hits` | Cache hits |
| `cache_misses` | Cache misses |
| `compilations` | Compile requests executed |

Cumulative session totals are acceptable when per-phase resets are unavailable.
