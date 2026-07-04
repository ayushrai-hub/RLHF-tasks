#include "statkit/vecstat.h"

double sk_mean(const double *v, int n)
{
    double s = 0.0;
    for (int i = 0; i < n; ++i) {
        s += v[i];
    }
    return s / (double)n;
}

double sk_var_unbiased(const double *v, int n)
{
    if (n < 2) {
        return 0.0;
    }
    double m = sk_mean(v, n);
    double s = 0.0;
    for (int i = 0; i < n; ++i) {
        double d = v[i] - m;
        s += d * d;
    }
    return s / (double)(n - 1);
}
