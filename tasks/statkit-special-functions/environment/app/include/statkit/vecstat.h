#ifndef STATKIT_VECSTAT_H
#define STATKIT_VECSTAT_H

/* Basic descriptive statistics over a contiguous array of doubles. */

/* Arithmetic mean of v[0..n-1]. Requires n >= 1. */
double sk_mean(const double *v, int n);

/* Unbiased sample variance (divides by n-1). Returns 0 for n < 2. */
double sk_var_unbiased(const double *v, int n);

#endif /* STATKIT_VECSTAT_H */
