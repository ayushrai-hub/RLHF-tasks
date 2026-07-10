#!/bin/bash
set -euo pipefail

# === Fix 1: config/profiles.toml — Profile overrides include_conditional to false ===
python3 << 'PATCH1'
src = open("/app/config/profiles.toml").read()
old = '''[analysis]
profile = "default"
include_conditional = false
max_chain_depth = 0'''
assert old in src, "Fix 1 failed"
src = src.replace(old, '''[analysis]
profile = "default"
include_conditional = true
max_chain_depth = 0''')
open("/app/config/profiles.toml", "w").write(src)
print("Fixed: profile override now uses correct include_conditional value")
PATCH1

# === Fix 2: pkg/checker/checker.go — Provability uses HasDirectEdge instead of IsReachable ===
python3 << 'PATCH2'
src = open("/app/pkg/checker/checker.go").read()
old = '''			provable := graph.HasDirectEdge(sub, super)

			obligations = append(obligations, types.Obligation{
				Sub:        sub,
				Super:      super,
				Via:        via,
				IsProvable: provable,
			})'''
assert old in src, "Fix 2 failed"
new = '''			provable := graph.IsReachable(sub, super)

			obligations = append(obligations, types.Obligation{
				Sub:        sub,
				Super:      super,
				Via:        via,
				IsProvable: provable,
			})'''
src = src.replace(old, new)
open("/app/pkg/checker/checker.go", "w").write(src)
print("Fixed: provability now uses transitive closure (IsReachable) instead of direct edge check")
PATCH2

# === Fix 3: pkg/checker/checker.go — breaking_rules includes all obligations, not just unprovable ===
python3 << 'PATCH3'
src = open("/app/pkg/checker/checker.go").read()
old = '''func findBreakingRules(rules []types.Rule, obligations []types.Obligation) []string {
	breakingSet := make(map[string]bool)

	for _, r := range rules {
		for _, o := range obligations {
			if r.SuperType == o.Via || r.SubType == o.Via {
				breakingSet[r.RuleID] = true
			}
		}
	}'''
assert old in src, "Fix 3 failed"
new = '''func findBreakingRules(rules []types.Rule, obligations []types.Obligation) []string {
	breakingSet := make(map[string]bool)

	for _, r := range rules {
		for _, o := range obligations {
			if !o.IsProvable && (r.SuperType == o.Via || r.SubType == o.Via) {
				breakingSet[r.RuleID] = true
			}
		}
	}'''
src = src.replace(old, new)
open("/app/pkg/checker/checker.go", "w").write(src)
print("Fixed: breaking_rules now only includes rules from unprovable obligations")
PATCH3

# === Fix 4: pkg/checker/checker.go — transitivity_holds uses > instead of == ===
python3 << 'PATCH4'
src = open("/app/pkg/checker/checker.go").read()
old = '''		TransitivityHolds: unprovable > 0,'''
assert old in src, "Fix 4 failed"
new = '''		TransitivityHolds: unprovable == 0,'''
src = src.replace(old, new)
open("/app/pkg/checker/checker.go", "w").write(src)
print("Fixed: transitivity_holds now correctly checks unprovable == 0")
PATCH4

# Rebuild and run
cd /app && go build -o bin/transitivity-checker ./cmd/transitivity-checker && ./bin/transitivity-checker data/rules.json output/results.json

echo "All fixes applied successfully."
