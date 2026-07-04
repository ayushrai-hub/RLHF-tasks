#ifndef STATKIT_SPECFUN_H
#define STATKIT_SPECFUN_H

/*
 * Special functions used by the statkit distribution layer.
 *
 * These are the *regularized* incomplete gamma and beta functions. Their exact
 * mathematical definitions live in docs/ALGORITHMS.md. The numerical method is
 * intentionally left to the implementation; only these signatures are frozen.
 *
 * All functions operate on IEEE-754 doubles and must return NAN for arguments
 * outside their documented domain.
 */

/* Regularized lower incomplete gamma  P(a, x),  a > 0,  x >= 0.  Range [0, 1]. */
double sk_gammap(double a, double x);

/* Regularized upper incomplete gamma  Q(a, x) = 1 - P(a, x). */
double sk_gammaq(double a, double x);

/* Regularized incomplete beta  I_x(a, b),  a > 0, b > 0, 0 <= x <= 1.  Range [0, 1]. */
double sk_betai(double a, double b, double x);

#endif /* STATKIT_SPECFUN_H */
