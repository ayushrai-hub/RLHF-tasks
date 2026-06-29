# Statistics Specification

## Nearest-Rank Percentile

    rank = ceil(q × n)
    rank clamped to [1, n]
    result = sorted[rank - 1]  (0-indexed)

Used for p50, p90, and p95 in `rental-report`.

Boundary example (n=7): p90 → ceil(0.9×7) = ceil(6.3) = 7 → sorted[6] (the last element).
Using floor(6.3)=6 → sorted[5] is WRONG.

## Population Standard Deviation

Divide by N (not N-1):

    mean = sum(values) / N
    variance = sum((v - mean)^2 for v in values) / N
    std = sqrt(variance)

## Banker's Rounding (HALF_EVEN)

Used when computing fee_cents = days × daily_rate_cents.
Round .5 cases to the nearest even integer.
Since days and daily_rate_cents are both integers, no fractional part arises in practice.

## Rental Duration Percentile (p90_duration_minutes)

Compute `duration_minutes = days_elapsed × 1440` for each closed checkout.
Sort all durations ascending. Apply nearest-rank at q=0.90:
`rank = ceil(0.90 × n)`, clamp to [1, n], return `sorted_durations[rank-1]`.

Boundary example (n=11): p90 → ceil(0.9×11) = ceil(9.9) = 10 → sorted_durations[9].
Using floor(9.9)=9 → sorted_durations[8] is WRONG.
