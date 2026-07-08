#include "kernels.h"
#include <math.h>

/*
 * polarity reports the sign carried by the negated gap -(a - b). The library
 * uses signed zero to remember which side a limit was approached from. When a
 * equals b the gap is positive zero, its negation is negative zero, and the
 * carried sign is negative, so polarity(a, a) is -1.
 */
double polarity(double a, double b)
{
    double gap = a - b;
    return copysign(1.0, -gap);
}

/*
 * magdiff returns sqrt(|a*a - b*b|), the magnitude of the difference of two
 * squares. The absolute value keeps the radicand non-negative, so the result
 * is always a real, non-negative number.
 */
double magdiff(double a, double b)
{
    return sqrt(fabs(a * a - b * b));
}
