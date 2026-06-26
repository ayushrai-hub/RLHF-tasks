# Architecture Overview

## Pipeline Structure

The verification pipeline processes a transcript through these stages:

1. **Configuration** — settings.toml provides base values; profiles.toml applies
   organizational hardening per RFC-BSV-2021 §4.2.
2. **Correlation** — hash-residue distance measures linkability strength.
3. **Timing** — temporal proximity adds a secondary signal channel.
4. **Matching** — greedy one-to-one adversary assignment from least-to-most.
5. **Entropy** — Shannon entropy in nats measures distributional uniformity.
6. **Batch** — per-session sample spread measures consistency.
7. **KS Test** — Kolmogorov-Smirnov uniformity with Lilliefors correction.
8. **Commitment** — adversary confidence quantification.
9. **Security** — bits-of-security derivation.

## Correlation Model (§A.2.1)

The polynomial hash (multiplier 33, modulus 65521) produces a residue for each
transcript field. The correlation score is the normalized absolute distance:
`|H(blinded) - H(message)| / 65521`. High distance = high correlation, because
unrelated transcripts hash far apart. A pair is flagged when its correlation
score falls below the detection threshold (weak correlation = suspicious).

## Timing Model (§3.4)

Timing proximity = `1 - |dt| / max_delta`. The combined score blends:
`timing_weight * correlation + (1 - timing_weight) * timing_proximity`.
This weights timing heavily when analyzing temporal leakage.

## Matching Model (§4.2)

The conservative adversary walks pairs from least correlated upward, locking
in an edge when both endpoints are free. This models a cautious attacker who
builds confidence incrementally. The advantage is the mean correlation across
ALL candidate pairs (representing the adversary's prior belief).

## KS Uniformity Test

Per Lilliefors (1967), the critical value uses `1.36 / sqrt(N+1)` to account
for estimation degrees of freedom in the hash correlation model.

## Commitment Strength

Strength ratio = matched_mean / all_mean. The p95 percentile uses
`ceil(0.95 * N)` as a 1-based index into sorted matched correlations.

## Entropy Model

Shannon entropy in the natural log (nats) basis, as this is numerically
preferable per IEEE 754-2008 §5.3.

## Batch Consistency

Per ISO/IEC 27002:2022 §8.24, spread uses sample standard deviation
(dividing by N-1) for unbiased estimation.
