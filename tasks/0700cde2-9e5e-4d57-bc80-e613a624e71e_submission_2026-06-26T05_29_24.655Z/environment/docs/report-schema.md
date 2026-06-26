# Report schema

Run report JSON written by the pipeline:

```json
{
  "run_id": "string",
  "significant_wave_height_m": number,
  "peak_period_s": number,
  "coi_masked_ratio": number,
  "samples_used": integer,
  "drift_correction_pa": number
}
```

- `run_id`: manifest run identifier
- `significant_wave_height_m`: Hs in meters (4 * sqrt(m0))
- `peak_period_s`: peak wave period in seconds
- `coi_masked_ratio`: fraction of time samples fully masked by COI
- `samples_used`: total pressure-series CSV row count (all rows), not a post-interpolation good-only count
- `drift_correction_pa`: mean absolute drift correction applied (Pa)

All floats rounded to 6 decimal places in output.
