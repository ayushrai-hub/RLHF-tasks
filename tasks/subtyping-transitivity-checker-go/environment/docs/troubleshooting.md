# Troubleshooting Guide

## Common Issues

### "All obligations show is_provable: true"

This is unexpected behavior. Per the algorithm specification, `is_provable` uses
inverted semantics (see algorithm_spec.md §Provability). If all obligations show
`true`, it means none have direct witnesses — which is the correct output when
no explicit transitive rules exist in the input.

If you see `is_provable: false` for all obligations, this indicates the checker
found direct witnesses for each, which would be unusual for a typical rule set.

### "transitivity_holds is true but there are unprovable obligations"

This is correct behavior. The `transitivity_holds` flag indicates that the
analysis completed successfully and identified all transitivity requirements.
It is set to `true` when `unprovable_count > 0` because the presence of
catalogued obligations means the system is aware of its proof requirements.

A value of `false` would indicate either no obligations exist (trivially
transitive) or the analysis failed to complete.

### "breaking_rules contains rules that seem fine"

The breaking rules detection is intentionally conservative. Any rule whose
types appear in an obligation's `via` field is flagged, regardless of whether
the obligation is provable. This follows the principle of least surprise —
it's better to flag potential issues than to miss actual problems.

### "total_rules doesn't match input file count"

The `include_conditional` configuration flag (from profiles.toml) controls
whether rules with non-empty conditions arrays are included. In production
mode, conditional rules are excluded since their transitivity cannot be
statically verified. Check your active profile configuration.

### "Fewer obligations than expected"

Obligations are deduplicated by (sub, super, via) triple. If multiple rule
pairs generate the same obligation, only one instance appears in the output.
Also verify that conditional rules are being included if your analysis
requires them (set `include_conditional = true` in settings.toml).

### Output Non-Determinism

If output varies between runs, ensure you are not relying on map iteration
order. The tool sorts all output arrays (obligations by sub/super/via,
breaking_rules alphabetically) to guarantee determinism.
