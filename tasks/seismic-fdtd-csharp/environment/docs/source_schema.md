# Source schema

The `source` subcommand reads a JSON description and writes a 1D NPY array of
float32 samples representing the source-time function. The output array has
length `round(duration_s * sample_rate_hz)` and is normalised so its maximum
absolute value equals exactly 1.

Common fields:

- `type`: one of `ricker`, `explosive`, `vibroseis`.
- `sample_rate_hz`: float, samples per second.
- `duration_s`: float, total record length in seconds.

Type-specific fields:

- `ricker`: `dominant_frequency_hz` (float, peak frequency `f` of the
  spectrum), `delay_s` (float, time shift `t0` of the central peak). The
  pre-normalisation analytic form is `(1 - 2*(pi*f*(t-t0))**2) * exp(-(pi*f*(t-t0))**2)`.
- `explosive`: `dominant_frequency_hz` (float, used as `f`), `delay_s` (float,
  centre of the underlying Gaussian). The pre-normalisation analytic form is
  the first time derivative of a Gaussian:
  `-2*alpha*(t-t0) * exp(-alpha*(t-t0)**2)` with `alpha = 2*(pi*f)**2`. With
  this choice the magnitude spectrum peaks at `f` Hz.
- `vibroseis`: `f_start_hz`, `f_end_hz` (floats, sweep endpoints in Hz),
  `taper_fraction` (float in `[0, 0.5)`, cosine-taper window applied to each
  end of the record as a fraction of the total duration). The pre-normalisation
  analytic form is a linear-rate chirp:
  `taper(t) * sin(2*pi*(f0*t + 0.5*(f1 - f0)/T * t**2))`
  where `T` is the duration and `taper(t)` is a Tukey-style window that ramps
  up over `taper_fraction*T` seconds at the start, holds at unity, then ramps
  back down over `taper_fraction*T` seconds at the end. The instantaneous
  frequency therefore rises linearly from `f_start_hz` at `t=0` to
  `f_end_hz` at `t=T`.

Sample times are `t_i = i / sample_rate_hz` for `i = 0, 1, ..., N-1`.
