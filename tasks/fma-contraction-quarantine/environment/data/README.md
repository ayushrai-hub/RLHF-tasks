# geokern

`geokern` is a small double-precision kernel library used by a geometry and
signal pipeline. It exposes ten public kernels grouped by translation unit and
one shared determinant helper:

- `src/geom.c` — `cross2`, `clamp01`
- `src/accum.c` — `recover`, `sign_of`
- `src/gain.c` — `cascade`, `roundtrip_residual`
- `src/flux.c` — `polarity`, `magdiff`
- `src/guard.c` — `domain_guard`, `horner`
- `src/helpers.c` — `det2` (internal, backs `cross2`)

`include/kernels.h` declares the public surface. `tools/kerneltest.c` is a
command-line probe that runs any kernel and prints the exact result.
`CONTRACTS.md` lists each kernel's documented invariant. `NUMERICS.md` covers
the floating-point model. The `samples/` directory holds the well-conditioned
inputs the release build was signed off against, one file per translation unit.

Build with `make` (release profile) or `make MODE=strict` (strict profile).
