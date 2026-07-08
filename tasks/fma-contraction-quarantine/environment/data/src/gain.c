#include "kernels.h"
#include <math.h>

/*
 * cascade applies two normalization stages: it divides a by b, then divides
 * that intermediate by c. Each division is a single IEEE rounding, so the
 * result is the staged quotient round(round(a / b) / c). The staging order is
 * part of the contract; the value is defined by performing the two divisions
 * in sequence, not by collapsing them into a single division by b*c.
 */
double cascade(double a, double b, double c)
{
    return (a / b) / c;
}

/*
 * roundtrip_residual reports how far x * (1 / x) lands from one. For every
 * finite nonzero x the residual is a handful of ulps at most.
 */
double roundtrip_residual(double x)
{
    double r = x * (1.0 / x);
    return fabs(r - 1.0);
}
