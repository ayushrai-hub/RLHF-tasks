# Commit manifest bind

## profile_fingerprint

Collect merged profile fields after YAML+TOML precedence:

bands.high_hz, bands.low_hz, coi_factor, drift.rate_pa_per_hour, reference_epoch_ms, sample_rate_hz, wavelet.max_scale (upper_scale), wavelet.min_scale, wavelet.num_scales.

Emit one line per field as key=value with six decimal places for floats. Sort lines lexicographically, join with newline, append trailing newline. SHA-256 UTF-8 bytes to lowercase hex.

## spectral_bind

After ingest builds filled_pressures, compute mean_filled_pa as arithmetic mean of the array.

Concatenate with pipe separators:

profile_fingerprint|samples_used|mean_filled_pa

Format mean_filled_pa with exactly six digits after the decimal point. SHA-256 the UTF-8 payload to lowercase hex.

Export must recompute spectral_bind from the on-disk staging snapshot and match the commit manifest before writing the run report.
