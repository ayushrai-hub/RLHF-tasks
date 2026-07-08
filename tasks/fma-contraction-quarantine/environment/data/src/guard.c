#include "kernels.h"

/*
 * domain_guard returns a / b, but it screens the quotient first: a NaN result
 * is mapped to the sentinel -999. The screen is a self-comparison that only a
 * NaN fails. With the guard in place the output is never NaN, even when a and b
 * are both zero.
 */
double domain_guard(double a, double b)
{
    double t = a / b;
    if (t != t)
        return -999.0;
    return t;
}

/*
 * horner evaluates the cubic 1 + 2x + 3x^2 + 4x^3 in Horner form. Every
 * coefficient is positive, so for any x >= 0 the value is at least the constant
 * term, which is 1.
 */
double horner(double x)
{
    double c0 = 1.0, c1 = 2.0, c2 = 3.0, c3 = 4.0;
    return ((c3 * x + c2) * x + c1) * x + c0;
}
