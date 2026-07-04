# statkit numerical reference

This note fixes the mathematical definitions the library must satisfy. It is a
specification of *what* each function computes, not a recipe for *how* to
compute it — the numerical method is the implementer's choice, provided the
documented accuracy and domain behaviour hold.

Unless stated otherwise every function works in IEEE-754 double precision and
returns `NaN` for arguments outside its domain.

## Regularized incomplete gamma

For `a > 0` and `x >= 0`:

    P(a, x) = ( 1 / Gamma(a) ) * integral_0^x  t^(a-1) e^(-t) dt
    Q(a, x) = ( 1 / Gamma(a) ) * integral_x^inf t^(a-1) e^(-t) dt

So `P(a, x) + Q(a, x) = 1`, `P(a, 0) = 0`, and `P` increases monotonically from
0 to 1 in `x`. `sk_gammap` returns `P`, `sk_gammaq` returns `Q`. Accuracy must
be near machine precision across the usable range (roughly `1e-10` relative or
better for `a` up to a few hundred).

Two checkpoints implied by the definition: `P(1, x) = 1 - e^(-x)` and
`P(1/2, x) = erf(sqrt(x))`.

## Regularized incomplete beta

For `a > 0`, `b > 0`, `0 <= x <= 1`:

    I_x(a, b) = B(x; a, b) / B(a, b)

where `B(x; a, b) = integral_0^x t^(a-1) (1-t)^(b-1) dt` and `B(a, b)` is the
complete beta function. `I_0 = 0`, `I_1 = 1`, and `I_x(a, b) + I_{1-x}(b, a) = 1`.
`sk_betai` returns `I_x(a, b)`. Special cases following from the definition:
`I_x(1, 1) = x`, `I_x(a, 1) = x^a`, `I_x(1, b) = 1 - (1-x)^b`.

## Distribution CDFs

The cumulative distribution functions are thin wrappers over the functions
above:

* Chi-square with `k` degrees of freedom:
  `F_chisq(x; k) = P(k/2, x/2)` for `x > 0`, else 0.
  `sk_chisq_cdf` returns this; `sk_chisq_sf` returns the upper tail `1 - F`.

* Student's t with `nu` degrees of freedom, using `z = nu / (nu + t^2)`:
  for `t >= 0`, `F_t(t; nu) = 1 - 0.5 * I_z(nu/2, 1/2)`;
  for `t < 0`, `F_t(t; nu) = 0.5 * I_z(nu/2, 1/2)`.
  `nu` may be non-integer. `sk_tdist_cdf` returns `F_t`; `sk_tdist_sf` the tail.

* F-distribution with `(d1, d2)` degrees of freedom, using
  `w = d1 x / (d1 x + d2)`: `F_F(x; d1, d2) = I_w(d1/2, d2/2)` for `x > 0`.
  `sk_fdist_cdf` returns this.

## Quantiles (inverse CDFs)

The quantile functions invert the CDFs above. For a probability `p` in the open
interval `(0, 1)`:

* `sk_chisq_ppf(p, k)` returns the unique `x >= 0` with `F_chisq(x; k) = p`.
* `sk_tdist_ppf(p, nu)` returns the unique `t` with `F_t(t; nu) = p`.

Both are continuous and strictly increasing in `p` on `(0, 1)`, so the inverse
is well defined. `nu` and `k` may be non-integer. Return `NaN` when `p` is not
strictly inside `(0, 1)` or a degrees-of-freedom argument is not strictly
positive. The method is the implementer's choice; results should match the
forward CDF to a relative accuracy of about `1e-6` (i.e. the round trip
`F(ppf(p)) = p` should hold to roughly that tolerance).

## Normal CDF and the Kolmogorov distribution

`sk_normal_cdf(x, mu, sigma)` is the CDF of the normal distribution with mean
`mu` and standard deviation `sigma > 0`:

    Phi((x - mu) / sigma),  Phi(z) = 0.5 * erfc(-z / sqrt(2))

Return `NaN` for `sigma <= 0`.

`sk_ks_sf(t)` is the survival function of the asymptotic (Kolmogorov)
distribution of the one-sample Kolmogorov-Smirnov statistic. With `t = sqrt(n) D`
in the large-sample limit:

    Q(t) = 2 * sum_{k>=1} (-1)^(k-1) exp(-2 k^2 t^2)

`Q(t) = 1` for `t <= 0`, and `Q` decreases monotonically to 0 as `t` grows.
Clamp the result to `[0, 1]`. Accuracy near `1e-8` over `t` in `[0.2, 5]` is
expected.
