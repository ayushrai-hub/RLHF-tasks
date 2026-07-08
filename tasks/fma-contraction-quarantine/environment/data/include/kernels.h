#ifndef KERNELS_H
#define KERNELS_H

/* Shared 2x2 determinant helper, linked from helpers.c. */
double det2(double a, double b, double c, double d);

/* Geometry kernels (geom.c). */
double cross2(double ax, double ay, double bx, double by);
double clamp01(double x);

/* Accumulation kernels (accum.c). */
double recover(double a, double b);
double sign_of(double x);

/* Ratio kernels (gain.c). */
double cascade(double a, double b, double c);
double roundtrip_residual(double x);

/* Flux kernels (flux.c). */
double polarity(double a, double b);
double magdiff(double a, double b);

/* Guarded kernels (guard.c). */
double domain_guard(double a, double b);
double horner(double x);

#endif
