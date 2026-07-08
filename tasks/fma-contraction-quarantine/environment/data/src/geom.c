#include "kernels.h"

/*
 * cross2 returns the planar cross product ax*by - ay*bx, computed through the
 * shared determinant helper. A vector is parallel to itself, so the cross
 * product of a vector with itself is exactly zero: cross2(ax, ay, ax, ay) == 0.
 * The callers use that exact zero as a collinearity test.
 */
double cross2(double ax, double ay, double bx, double by)
{
    return det2(ax, by, ay, bx);
}

/*
 * clamp01 saturates x into the closed unit interval [0, 1]. The output never
 * leaves [0, 1] for any finite input.
 */
double clamp01(double x)
{
    if (x < 0.0)
        return 0.0;
    if (x > 1.0)
        return 1.0;
    return x;
}
