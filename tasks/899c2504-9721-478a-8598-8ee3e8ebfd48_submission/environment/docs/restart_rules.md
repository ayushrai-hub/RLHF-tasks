# Restart gating

A unit is **gated** when it needs restart and readiness is yes (after trim and lowercasing per `contracts.md`).

A unit is **blocked** when it needs restart but readiness is not yes.

`restart_plan` is the ordered list of gated unit names only—the units cleared to restart now. It must not include blocked units. `gated_units` uses the same names in the same order as `restart_plan`.

Required unit order comes from `/app/environment/config/service_rules.toml`. Only units listed in `/app/environment/data/units_allowlist.txt` are considered.
