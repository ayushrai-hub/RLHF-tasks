# Kernel contracts

Each kernel carries a documented mathematical invariant. The invariant is what
the library promises about the value the kernel returns; it is stated for the
ideal real-number computation and holds for the strict-profile build. Each
invariant has a short id used to refer to it.

| kernel | translation unit | invariant id | invariant |
|---|---|---|---|
| cross2 | geom.c | self_cross_zero | the cross product of a vector with itself is exactly zero: cross2(x, y, x, y) == 0 |
| clamp01 | geom.c | in_unit | the result lies in the closed interval from zero to one |
| recover | accum.c | absorbed_zero | when a + b rounds back to a, the result is exactly zero |
| sign_of | accum.c | sign_set | the result is one of minus one, zero, or one |
| cascade | gain.c | staged_quotient | the result equals the staged quotient: a divided by b, then that divided by c, each a single rounding |
| roundtrip_residual | gain.c | small_residual | the residual is at most a few ulps of one |
| polarity | flux.c | equal_negative | for equal inputs the carried sign is negative, so the result is minus one |
| magdiff | flux.c | nonneg_real | the result is real and not negative |
| domain_guard | guard.c | never_nan | the result is never NaN; an out-of-domain quotient that comes back NaN is replaced by the sentinel |
| horner | guard.c | ge_constant | for non-negative x the value is at least the constant term, one |

The shared helper `det2` in helpers.c is internal and carries no public
invariant of its own; it backs cross2.
