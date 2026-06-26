# Processing contract

## Pipeline stages

1. **ingest** — load manifest, merge profiles, drift-correct and gap-fill series, write /app/state/spectra-ingest-snapshot.json and /app/state/spectra-commit-bind.json per staging-contract.md.
2. **export** — validate commit bind against staging, run Morlet spectra on staged filled_pressures only, write report JSON.
3. **process** — ingest then export (default for /app/scripts/run-spectra-pipeline.sh).

## Ingest processing

1. Load run manifest JSON (paths are absolute or relative to /app/fixtures/).
2. Merge processing profile YAML with TOML site overlay per /app/docs/config-precedence.md.
3. Read pressure series CSV (timestamp_ms, pressure_pa, quality_flag).
4. Subtract linear drift from pressure using merged profile drift block.
5. Linearly interpolate missing samples (quality_flag = 0).
6. Persist filled_pressures array and commit bind per commit-manifest.md.

## Export processing

1. Load staging snapshot and commit manifest from /app/state/.
2. Validate spectral_bind and profile_fingerprint per commit-manifest.md.
3. Run Morlet CWT on filled_pressures from staging (do not re-read CSV for spectral input).
4. Write run report JSON per /app/docs/report-schema.md.

## Pressure units

The pressure_pa column stores absolute pressure in Pascals (not hectopascals). Drift rate_pa_per_hour is also Pascals per hour. Apply drift subtraction in the same unit space as the CSV values.

## Drift

corrected_pa = raw_pa - drift.rate_pa_per_hour * ((timestamp_ms - drift.reference_epoch_ms) / 3600000.0)

## Gaps

Never zero-fill. Linear interpolation between nearest good neighbors; edge gaps use nearest good value.

## Wavelet / COI

Morlet wavelet at scales from profile wavelet.min_scale .. wavelet.upper_scale (inclusive, logarithmic steps wavelet.num_scales). Use coi_factor from merged profile (default sqrt(2)).

Morlet power at time index center, scale s, sample rate f_s Hz:

1. Window half-width = ceil(2 * s) sample indices on each side of center (skip out-of-range indices).
2. For offset k in [-half, half] with valid index idx = center + k, let t = k / f_s and kernel w(k) = exp(-t²/(2s²)) * cos(5t/s).
3. Accumulate total = Σ η[idx] * w(k) over valid terms and cnt = count of those terms.
4. Power = (total / cnt)².

Cone of influence (integer half-width): for each scale s, define coi_w = ceil(coi_factor * s) as an integer sample count. Time index t is COI-valid when at least one scale satisfies coi_w <= t < n - coi_w. Wavelet power at (t, s) contributes to peak search only when that scale's coi_w <= t < n - coi_w.

Scale-to-frequency mapping: for scale s, use freq_hz = sample_rate_hz / s when testing band limits and peak selection.

## Summaries

- significant_wave_height_m = 4 * sqrt(m0) where m0 is mean squared elevation at COI-valid time indices only.
- peak_period_s = 1 / f_peak where f_peak is the freq_hz of maximum Morlet power among COI-valid (t, s) pairs with freq_hz in [bands.low_hz, bands.high_hz].
- coi_masked_ratio = fraction of time indices that are not COI-valid (0..1).
- samples_used = total CSV data rows in the input series file (every row), including rows with quality_flag = 0 that were gap-filled.

## Constants

RHO_SEA = 1025, G = 9.81, sample rate from profile sample_rate_hz only (never manifest metadata).
