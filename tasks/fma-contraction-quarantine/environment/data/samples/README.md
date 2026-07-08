# Sample inputs

Each file holds the well-conditioned arguments one translation unit's kernels
were exercised with during sign-off, one record per line: the kernel name, a
tab, then the space-separated double arguments. These are the inputs the
release build was validated against and matched the strict build on.

- `geom_samples.tsv` — cross2, clamp01
- `accum_samples.tsv` — recover, sign_of
- `gain_samples.tsv` — cascade, roundtrip_residual
- `flux_samples.tsv` — polarity, magdiff
- `guard_samples.tsv` — domain_guard, horner
