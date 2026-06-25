# Imaging, QC, and sweep schemas

All CSV outputs in this stage (`avo` and the sweep `parameters.csv`) are plain
UTF-8 text with no byte-order mark. The very first byte of the file is the
first character of the header row, so write them with a BOM-free encoding (for
example `new UTF8Encoding(false)` rather than the default `Encoding.UTF8`).

## image (RTM)

Reverse-time migration. Forward-propagates the source field, back-propagates
the receiver data, and forms a zero-lag cross-correlation imaging condition.

JSON fields:

- `model_dir`: directory with `vp.npy`, `vs.npy`, `rho.npy`, `qp.npy`, `qs.npy`.
- `grid`: `{ "dx": float, "dz": float }`.
- `source`: `{ "path": str, "x": float, "z": float }` — pressure source as in
  `simulate`.
- `receivers`: `{ "x_start": float, "x_end": float, "n": int, "z": float }`.
- `shot_gather`: path to the pre-computed shot-gather NPY produced by
  `simulate`.
- `time_step_s`, `n_steps`: as in `simulate`.
- `pml`: `{ "thickness": int, "r_coeff": float }`. PML is always enabled for
  RTM.

Output (single positional argument is an output directory):

- `image.npy`: 2D float32 array of shape `(nz, nx)` holding the imaging
  condition (sum over time of forward source field times back-propagated
  receiver field at each cell).

## avo

Amplitude-versus-offset analysis. Picks the peak reflection amplitude on each
receiver and fits the Shuey two-term model `A(theta) = A0 + B * sin^2(theta)`.

JSON fields:

- `shot_gather`: path to NPY shot gather.
- `time_axis`: path to NPY time axis.
- `source_x`, `source_z`: floats, source position in metres.
- `receivers`: same as in `simulate`.
- `reflector_depth_m`: float, depth of the reflector to analyse.
- `overburden_vp_m_s`: float, P-velocity above the reflector (used to convert
  source-receiver offset into incidence angle via straight-ray approximation).
- `pick_window_s`: 2-element array `[t_min, t_max]` in seconds, restricting
  the peak search to this window.

Output (single positional argument is an output CSV path):

- CSV with header row `offset_m,angle_rad,amplitude` followed by one data row
  per receiver, then a trailing row `fit,intercept,gradient` where
  `amplitude` is the peak absolute value of `vz` in the pick window and
  `intercept = A0`, `gradient = B` come from the linear regression
  `amplitude ~ intercept + gradient * sin^2(angle_rad)`.

## qc

Quality-metric report.

JSON fields:

- `shot_gather`, `time_axis`: paths to NPY arrays.
- `source`: `{ "x": float, "z": float, "dominant_frequency_hz": float }`.
- `receivers`: same as `simulate`.
- `overburden_vp_m_s`: float, used to compute resolution and illumination.
- `noise_window_s`: 2-element array `[t0, t1]` in seconds; defines the
  pre-signal noise window used to estimate the noise floor (RMS).
- `target_depths_m`: array of floats; depths at which illumination counts are
  evaluated.
- `target_xs_m`: array of floats; horizontal positions used for illumination.

Output (single positional argument is an output JSON path):

    {
      "snr_db": float,                       // 20*log10(peak_signal / rms_noise)
      "dominant_wavelength_m": float,        // overburden_vp / dominant_frequency
      "vertical_resolution_m": float,        // dominant_wavelength / 4 (Rayleigh quarter-wavelength)
      "illumination": [                      // one entry per (x, z) pair from
                                             // the cartesian product of target_xs_m
                                             // and target_depths_m (z outer, x inner)
        {"x": float, "z": float, "n_rays": int}
      ]
    }

For illumination, count the number of source-receiver pairs whose
straight-line midpoint falls within `bin_half` of the target horizontal
position, where `bin_half = receiver_spacing / 2` and `receiver_spacing =
(x_end - x_start) / (n - 1)`. A pair also has to satisfy the angle cap: the
half-offset / target-depth ratio gives an incidence angle of at most 45
degrees, i.e. `atan2(|x_r - x_s|/2, target_depth) <= pi/4`. Treat the single
source position from the `source` field as the only source.

## sweep

Parametric source-spacing sweep. Runs the same survey at each requested source
spacing and produces an illumination map plus a parameters CSV.

JSON fields:

- `base_config`: the JSON object that would be passed to `simulate` (used as a
  template).
- `source_spacings_m`: array of floats; for each spacing s, place sources at
  the centre of the survey and at offsets +/- s, +/- 2s, ... that still fit
  within `[x_start, x_end]`.
- `survey_x_start`, `survey_x_end`: floats, range of allowed source x
  positions.
- `target_depth_m`: float, depth at which the illumination map is evaluated.
- `target_xs_m`: array of floats, horizontal target positions.

Output (single positional argument is an output directory):

- `parameters.csv`: header `spacing_m,n_sources` followed by one row per
  spacing, in the same order as `source_spacings_m`.
- `illumination_map.npy`: 2D float32 array of shape `(n_spacings, n_target_xs)`
  where entry `(i, j)` is the total ray count over all sources for spacing `i`
  at target position `(target_xs_m[j], target_depth_m)`, using the same
  midpoint-bin and angle-cap rule as the `qc` subcommand (with the same
  receiver-spacing derived bin width).

The sweep does not need to re-run full FDTD simulations — only the illumination
geometry needs to be evaluated per spacing.
