# Changelog

## 0.4.0
- Performance team enabled the aggressive release profile for shipping builds.

## 0.3.0
- Split the shared determinant term out into helpers.c so geom.c and any future
  geometry code share one definition.
- Added domain_guard with a NaN screen and the -999 sentinel.

## 0.2.0
- Added the flux and gain kernels (polarity, magdiff, cascade,
  roundtrip_residual).
- Documented every kernel's invariant in CONTRACTS.md.

## 0.1.0
- Initial release: geom and accum kernels, the kerneltest probe, and the
  well-conditioned sample inputs.
