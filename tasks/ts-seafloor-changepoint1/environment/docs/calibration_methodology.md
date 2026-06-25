# PSON Calibration Methodology Overview

## Linear Secondary Calibration

PSON pressure transducers apply a two-parameter linear calibration on top of the factory calibration:

    calibrated_kPa = raw_value × gain + offset

where `raw_value` is the value stored in the database, `gain` is dimensionless, and `offset` is in kPa.
Parameters are station-specific; see the main dossier (seismology_ops_dossier.md) for exact values.

## Displacement Estimation

Vertical seafloor displacement is derived from the mean calibrated pressure anomaly over an event window:

    displacement_m = mean_anomaly_kPa × 0.1

The factor 0.1 m/kPa is derived from seawater density ≈ 1027 kg/m³ and g = 9.81 m/s² at PSON depths.

## Change-Point Detection Pipeline

1. Apply secondary calibration (gain + offset)
2. Remove trend with a 10-day rolling quadratic polynomial fit
3. Compute robust Z-score: Z = (x − median) / (1.4826 × MAD)
4. Flag windows where Z exceeds station-specific threshold for the minimum required duration
5. Score each candidate window using a Bayesian log-likelihood ratio (log Bayes factor)
6. Assign confidence score via sigmoid transformation of the log Bayes factor

For full algorithm details, see Section 9 of seismology_ops_dossier.md.
