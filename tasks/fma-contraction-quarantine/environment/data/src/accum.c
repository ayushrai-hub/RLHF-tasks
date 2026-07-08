#include "kernels.h"

/*
 * recover returns (a + b) - a. The library uses it to peel a small increment
 * back off a running total. When b is so small beside a that a + b rounds back
 * to a, the increment was absorbed and recover returns exactly 0; otherwise it
 * returns the part of b that survived the addition.
 */
double recover(double a, double b)
{
    return (a + b) - a;
}

/*
 * sign_of returns -1, 0, or 1 according to the sign of x. The result is always
 * one of those three values.
 */
double sign_of(double x)
{
    return (double)((x > 0.0) - (x < 0.0));
}
