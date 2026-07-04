#include "statkit/distrib.h"
#include "statkit/specfun.h"

#include <math.h>

double sk_tdist_cdf(double t, double nu)
{
    if (nu <= 0.0) {
        return NAN;
    }
    double z = nu / (nu + t * t);
    double ib = sk_betai(nu / 2.0, 0.5, z);
    if (t >= 0.0) {
        return 1.0 - 0.5 * ib;
    }
    return 0.5 * ib;
}

double sk_tdist_sf(double t, double nu)
{
    return 1.0 - sk_tdist_cdf(t, nu);
}
