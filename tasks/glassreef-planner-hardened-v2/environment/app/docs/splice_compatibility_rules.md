# Splice compatibility rules

Lua policy files under /app/policies/splice define which kit codes may repair each splice family and the compatibility bonus for that family/kit pair. /app/scripts/run_glassreef_planner.sh emits these rules to /app/build/splice_rules.csv before running the Rust planner.

A ship can repair a span only if at least one of its kit codes is compatible with the span splice_family. If a ship has more than one compatible kit, or the emitted rules repeat the same family and kit pair, the highest applicable compatibility bonus is used for that ship/span pair after duplicate family/kit rows are resolved by the last row in the generated CSV.
