#include "kernels.h"

/*
 * det2 evaluates the signed area term a*b - c*d. It is the one shared
 * primitive in the library: the geometry layer routes every orientation and
 * cross-product computation through it so the determinant has a single
 * definition. It is an out-of-line function on purpose, so callers in other
 * translation units reach it by an ordinary call.
 */
double det2(double a, double b, double c, double d)
{
    return a * b - c * d;
}
