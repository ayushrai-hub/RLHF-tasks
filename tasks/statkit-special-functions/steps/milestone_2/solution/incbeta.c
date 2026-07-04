#include "statkit/specfun.h"

#include <math.h>

/* Modified-Lentz continued fraction for the incomplete beta. */
static double betacf(double a, double b, double x)
{
    const double FPMIN = 1e-300;
    double qab = a + b;
    double qap = a + 1.0;
    double qam = a - 1.0;
    double c = 1.0;
    double d = 1.0 - qab * x / qap;
    if (fabs(d) < FPMIN) {
        d = FPMIN;
    }
    d = 1.0 / d;
    double h = d;
    for (int m = 1; m < 1000; ++m) {
        double m2 = 2.0 * m;
        double aa = m * (b - m) * x / ((qam + m2) * (a + m2));
        d = 1.0 + aa * d;
        if (fabs(d) < FPMIN) {
            d = FPMIN;
        }
        c = 1.0 + aa / c;
        if (fabs(c) < FPMIN) {
            c = FPMIN;
        }
        d = 1.0 / d;
        h *= d * c;
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
        d = 1.0 + aa * d;
        if (fabs(d) < FPMIN) {
            d = FPMIN;
        }
        c = 1.0 + aa / c;
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
    return h;
}

double sk_betai(double a, double b, double x)
{
    if (x < 0.0 || x > 1.0 || a <= 0.0 || b <= 0.0) {
        return NAN;
    }
    double bt;
    if (x == 0.0 || x == 1.0) {
        bt = 0.0;
    } else {
        bt = exp(lgamma(a + b) - lgamma(a) - lgamma(b)
                 + a * log(x) + b * log(1.0 - x));
    }
    if (x < (a + 1.0) / (a + b + 2.0)) {
        return bt * betacf(a, b, x) / a;
    }
    return 1.0 - bt * betacf(b, a, 1.0 - x) / b;
}
