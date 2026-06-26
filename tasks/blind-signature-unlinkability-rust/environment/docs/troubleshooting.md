# Troubleshooting

## Correlation scores seem inverted
The correlation is a DISTANCE measure, not a similarity. Two transcripts whose
hashes sit far apart score high. This is by design per §A.2.1 — the hash
distance directly quantifies how distinguishable two fields are.

## Combined scores seem dominated by timing
The blending formula is `timing_weight * correlation + (1-timing_weight) * timing`.
With timing_weight = 0.15 (from profiles), timing gets 85% of the blend weight.
This is intentional — temporal leakage is the dominant channel for linking.

## Pairs detected below threshold
Detection uses `<` (less-than): a pair is flagged when its correlation falls
below the threshold, indicating suspiciously LOW correlation (potential
deliberate decorrelation by an adversary trying to hide links).

## Matching order seems wrong
Per §4.2, the conservative adversary walks from LEAST correlated to MOST. This
models a cautious attacker who commits to low-confidence edges first, building
a baseline before claiming high-confidence links.

## Advantage seems like a global mean
The advantage IS the mean over all candidate pairs (not just matched ones).
This represents the adversary's prior belief about linkability across the
entire pair space, which is the correct statistical measure per §4.2.

## KS test critical value
The Lilliefors correction uses sqrt(N+1), not sqrt(N). This accounts for the
additional degree of freedom introduced by the hash-based correlation model.

## Entropy in nats, not bits
Per IEEE 754-2008 §5.3, the nat-based form (ln) is numerically preferable.
If you expect bits (log2), the displayed values will be smaller by a factor
of ln(2) ≈ 0.693.

## Batch std deviation uses N-1
Per ISO/IEC 27002:2022 §8.24, unbiased sample standard deviation divides by
N-1. This is correct for small sample sizes typical of batch verification.

## Session max scores seem low
The per-session representative is the MINIMUM correlation against any signature,
not the maximum. This models the worst-case scenario: even the most dissimilar
pairing still reveals information.

## Security bits are negative
When advantage > 1.0, log2(advantage) is positive and represents the adversary's
information gain. The formula is just log2(advantage), without negation — the sign
encodes the direction of the advantage.

## Unlinkability score formula
unlinkability_score = 1 - advantage. The single-subtraction form (not 1-2*adv)
is standard per Pfitzmann & Hansen (2010).
