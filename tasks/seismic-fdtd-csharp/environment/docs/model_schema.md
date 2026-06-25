# Model schema

The `model` subcommand reads a JSON configuration and writes five NPY arrays
to the output directory: `vp.npy`, `vs.npy`, `rho.npy`, `qp.npy`, `qs.npy`.
Each array has shape `(nz, nx)` and dtype float32. Index `[iz, ix]` corresponds
to a cell centred at position `(ix * dx, iz * dz)` measured from the
top-left corner of the model.

Top-level JSON fields:

- `grid`: object with `nx`, `nz` (integers, number of cells in x and z),
  and `dx`, `dz` (floats, cell sizes in metres).
- `layers`: array of layer objects, ordered top to bottom but not required to
  be contiguous. Each layer object has `top_z` and `bottom_z` (metres, with
  `top_z < bottom_z`), and the physical parameters `vp`, `vs`, `rho`, `qp`,
  `qs` (floats). The layer that contains a cell's centre depth wins.
- `salt_bodies`: optional array of polygon objects, each with `polygon`
  (closed polygon as an array of `[x, z]` vertex pairs in metres, last vertex
  need not repeat the first) and the same physical parameters as layers. A
  cell whose centre lies inside any polygon takes that polygon's parameters
  and overrides the layered background.
- `faults`: optional array of fault objects, each with `x0`, `z0`, `x1`, `z1`
  (line endpoints in metres) and `throw` (vertical offset in metres). A cell
  with centre `(cx, cz)` is on the hanging-wall side of a fault iff
  `(z1 - z0) * (cx - x0) - (x1 - x0) * (cz - z0) > 0` (i.e., to the right of
  the directed line when z increases downward). Hanging-wall cells look up
  their layer at depth `(centre_z - throw)` instead of `centre_z`, simulating
  a downthrown block on the right side. Apply faults before salt bodies; salt
  bodies override both layers and faulted cells. Faults stack additively when
  multiple are listed. When the stacked throw pushes a cell's lookup depth above
  the top of the model (a negative depth), use the topmost layer rather than
  reading a negative depth.

Water layers (the topmost layer in marine models) typically have `vs = 0`,
which must propagate to the `vs.npy` array.
