# Processing contract

## Pipeline

1. Load run manifest JSON (paths are absolute or relative to `/app/fixtures/`).
2. Merge processing profile YAML with TOML site overlay per `/app/docs/config-precedence.md`.
3. Read pressure series CSV (`timestamp_ms`, `pressure_hpa`, `quality_flag`).
4. Subtract linear drift from pressure using merged profile drift block.
5. Linearly interpolate missing samples (`quality_flag` = 0).
6. Convert corrected pressure anomaly to elevation meters: `(p - mean(p)) / (1025 * 9.81)`.
7. Morlet CWT power on elevation; apply cone-of-influence mask before spectral summaries.
8. Write run report JSON per `/app/docs/report-schema.md`.

## Drift

`corrected_pa = raw_pa - drift.rate_pa_per_hour * ((timestamp_ms - drift.reference_epoch_ms) / 3600000.0)`

## Gaps

Never zero-fill. Linear interpolation between nearest good neighbors; edge gaps use nearest good value.

## Wavelet / COI

Morlet wavelet at scales from profile `wavelet.min_scale` .. `wavelet.upper_scale` (inclusive, logarithmic steps `wavelet.num_scales`). Use `coi_factor` from merged profile (default `sqrt(2)`).

**Morlet power:** at time index `center`, scale `s`, sample rate `f_s` Hz:

1. Window half-width = `ceil(2 * s)` sample indices on each side of `center` (skip out-of-range indices).
2. For offset `k` in `[-half, half]` with valid index `idx = center + k`, let `t = k / f_s` and kernel `w(k) = exp(-t²/(2s²)) * cos(5t/s)`.
3. Accumulate `total = Σ η[idx] * w(k)` over valid terms and `cnt` = count of those terms.
4. **Power = (total / cnt)²** — divide by `cnt` to form the **mean** windowed product, then square. Squaring the raw sum `total` without mean normalization is incorrect and will fail coarse-scale probe manifests.

**Cone of influence (integer half-width):** for each scale `s`, define `coi_w = ceil(coi_factor * s)` as an integer sample count (not a floating comparison). Time index `t` is **COI-valid** when at least one scale satisfies `coi_w <= t < n - coi_w`. Wavelet power at `(t, s)` contributes to peak search only when that scale’s `coi_w <= t < n - coi_w`.

**Scale-to-frequency mapping:** for scale `s`, use `freq_hz = sample_rate_hz / s` when testing band limits and peak selection. Do not substitute textbook Morlet center-frequency formulas; band limits apply to this mapping.

## Summaries

- `significant_wave_height_m` = `4 * sqrt(m0)` where `m0` is mean squared elevation at **COI-valid** time indices only.
- `peak_period_s` = `1 / f_peak` where `f_peak` is the `freq_hz` of maximum Morlet power among COI-valid `(t, s)` pairs with `freq_hz` in `[bands.low_hz, bands.high_hz]`.
- `coi_masked_ratio` = fraction of time indices that are not COI-valid (0..1).
- `samples_used` = total CSV data rows in the input series file (every row), including rows with `quality_flag = 0` that were gap-filled.

## Constants

`RHO_SEA = 1025`, `G = 9.81`, sample rate from profile `sample_rate_hz`.
