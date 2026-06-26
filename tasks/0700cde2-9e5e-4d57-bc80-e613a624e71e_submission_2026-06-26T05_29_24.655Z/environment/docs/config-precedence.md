# Configuration precedence

Processing configuration merges two sources:

1. **YAML profile** referenced by manifest field `profile` (storm processing defaults).
2. **TOML overlay** referenced by manifest field `toml_overlay` (site calibration).

Merge order:

- Start from YAML map (deep copy).
- Apply TOML overlay keys; **TOML wins on conflicts** at any depth.

Drift and wavelet blocks merge field-by-field; nested tables in TOML override YAML nested maps.

Do not read sample rate from manifest metadata — use merged profile `sample_rate_hz` only.
