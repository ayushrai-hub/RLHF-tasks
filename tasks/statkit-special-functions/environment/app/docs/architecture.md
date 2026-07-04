# statkit architecture

statkit is a small C11 toolkit for classical hypothesis testing without any
third-party dependency beyond the C math library.

```
include/statkit/   public headers (frozen API)
src/               libstatkit.a sources
  incgamma.c       regularized incomplete gamma  P, Q
  chisq.c          chi-square CDF / SF (on top of incgamma)
  incbeta.c        regularized incomplete beta  I_x
  student.c        Student's t CDF / SF (on top of incbeta)
  fdist.c          F-distribution CDF (on top of incbeta)
  invdist.c        quantiles (inverse CDFs) for chi-square and t
  ksdist.c         normal CDF + Kolmogorov survival function
  vecstat.c        mean / unbiased variance helpers
  jsonout.c        minified JSON buffer helpers
cli/               statctl command-line tool
  specparse.c      .spec suite parser
  statctl.c        driver: parse, run tests, correct, emit report
tests/             frozen C acceptance suite (make test)
docs/              this file, ALGORITHMS.md, FORMAT.md
data/fixtures/     sample .spec inputs
```

The distribution layer never touches transcendental approximations directly; it
routes everything through the two incomplete special functions in `specfun.h`.
That keeps the numerically delicate code in one place and lets the CDFs stay
trivial. The quantile functions in `invdist.c` invert those CDFs. `statctl` in
turn is pure glue: it parses a suite, calls the distribution and quantile layers
for p-values, critical values, and intervals, applies the suite-level
multiple-testing correction, and serialises the result.

Build with `make`; run the acceptance suite with `make test`.
