# Simulate schema

The `simulate` subcommand runs a 2D P-SV elastic FDTD shot and writes:

- `shot_gather.npy`: 2D float32 array of vertical-velocity samples at receivers,
  shape `(n_steps, n_receivers)`. Row `t` is the snapshot of every receiver's
  `vz` value at time-step `t`.
- `time.npy`: 1D float32 array of length `n_steps` giving sample times in
  seconds, `t_i = i * time_step_s`.
- `snapshots/snap_TTTTTT.npy`: 2D snapshots of the `vz` field of shape
  `(nz, nx)`, written every `snapshot_interval` steps and named with the
  zero-padded six-digit step index.

JSON fields:

- `model_dir`: path to the directory containing `vp.npy`, `vs.npy`, `rho.npy`,
  `qp.npy`, `qs.npy` (as produced by the `model` subcommand).
- `grid`: `{ "dx": float, "dz": float }` (cell sizes in metres; nx and nz come
  from the model arrays).
- `source`: `{ "path": str, "x": float, "z": float, "kind": "pressure" | "vz" }`
  where `path` is an NPY source-time series, `x` and `z` are the injection
  coordinates in metres, and `kind` selects pressure injection (added equally
  to sigma_xx and sigma_zz of the nearest cell) or a vertical velocity
  injection (added to vz of the nearest cell).
- `receivers`: `{ "x_start": float, "x_end": float, "n": int, "z": float }`
  describing a uniform horizontal line of receivers between `x_start` and
  `x_end` inclusive.
- `time_step_s`: float, FDTD time-step `dt` in seconds.
- `n_steps`: integer, total number of FDTD updates.
- `pml`: `{ "thickness": int, "enabled": bool, "r_coeff": float }`. When
  enabled, apply a polynomial absorbing-damping zone of `thickness` cells on
  all four sides. Each cell in the zone, with depth `d` (in cells) into the
  zone, multiplies every field component (vx, vz, sigma_xx, sigma_zz,
  sigma_xz) by `exp(-damping(d) * dt)` per step, where
  `damping(d) = (3 * |log(r_coeff)| / (thickness * dt)) * (d / thickness)**2`.
  The corner cells take the maximum of the x-distance and z-distance into the
  zone. When disabled, leave the boundary as a free zero-stress edge.
- `attenuation`: `{ "enabled": bool, "reference_frequency_hz": float }`. When
  enabled, apply a single-mechanism standard-linear-solid (SLS) attenuation
  by multiplying every stress component by `exp(-(pi * f_ref * dt) / Q)` per
  step, using `Q = qp.npy[iz, ix]` for sigma_xx, sigma_zz, and sigma_xz.
  Cells with non-finite Q (e.g. water with Q = 1e6) skip the multiply. When
  disabled, treat the medium as purely elastic.
- `snapshot_interval`: integer, write a `vz` snapshot every this many steps.
  Set to a non-positive value to disable snapshots.
