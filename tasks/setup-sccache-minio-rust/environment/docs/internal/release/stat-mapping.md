# Stat mapping

Per-phase `hits`, `misses`, and `compilations` in the release benchmark JSON come from that phase's `sccache --show-stats` output:

| JSON field | `sccache --show-stats` label |
|------------|------------------------------|
| `hits` | Cache hits |
| `misses` | Cache misses |
| `compilations` | Non-cacheable compilations |

Do not map `compilations` from Compile requests executed.
