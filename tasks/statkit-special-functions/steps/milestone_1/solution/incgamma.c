#include "statkit/specfun.h"

#include <math.h>

/* Power-series expansion for P(a, x), accurate for x < a + 1. */
static double gser(double a, double x)
{
    if (x <= 0.0) {
        return 0.0;
    }
    double ap = a;
    double sum = 1.0 / a;
    double del = sum;
    for (int n = 0; n < 1000; ++n) {
        ap += 1.0;
        del *= x / ap;
        sum += del;
        if (fabs(del) < fabs(sum) * 1e-16) {
            break;
        }
    }
    return sum * exp(-x + a * log(x) - lgamma(a));
}

/* Modified-Lentz continued fraction for Q(a, x), accurate for x >= a + 1. */
static double gcf(double a, double x)
{
    const double FPMIN = 1e-300;
    double b = x + 1.0 - a;
    double c = 1.0 / FPMIN;
    double d = 1.0 / b;
    double h = d;
    for (int i = 1; i < 1000; ++i) {
        double an = -(double)i * ((double)i - a);
        b += 2.0;
        d = an * d + b;
        if (fabs(d) < FPMIN) {
            d = FPMIN;
        }
        c = b + an / c;
        if (fabs(c) < FPMIN) {
            c = FPMIN;
        }
        d = 1.0 / d;
        double del = d * c;
        h *= del;
        if (fabs(del - 1.0) < 1e-16) {
            break;
        }
    }
    return exp(-x + a * log(x) - lgamma(a)) * h;
}

double sk_gammap(double a, double x)
{
    if (x < 0.0 || a <= 0.0) {
        return NAN;
    }
    if (x == 0.0) {
        return 0.0;
    }
    if (x < a + 1.0) {
        return gser(a, x);
    }
    return 1.0 - gcf(a, x);
}

double sk_gammaq(double a, double x)
{
    if (x < 0.0 || a <= 0.0) {
        return NAN;
    }
    if (x == 0.0) {
        return 1.0;
    }
    if (x < a + 1.0) {
        return 1.0 - gser(a, x);
    }
    return gcf(a, x);
}
