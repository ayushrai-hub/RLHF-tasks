/* Milestone 2 acceptance: regularized incomplete beta I_x(a,b). */
#include "statkit/specfun.h"
#include "runner.h"

int main(void)
{
    printf("test_incbeta\n");

    /* Identity: I_x(1,1) = x. */
    for (double x = 0.05; x < 1.0; x += 0.1) {
        SK_CLOSE(sk_betai(1.0, 1.0, x), x, 1e-12);
    }

    /* Identity: I_x(a,1) = x^a  and  I_x(1,b) = 1 - (1-x)^b. */
    for (double x = 0.1; x < 1.0; x += 0.2) {
        SK_CLOSE(sk_betai(3.0, 1.0, x), pow(x, 3.0), 1e-12);
        SK_CLOSE(sk_betai(1.0, 4.0, x), 1.0 - pow(1.0 - x, 4.0), 1e-12);
    }

    /* Symmetry: I_x(a,b) + I_{1-x}(b,a) = 1. */
    for (double a = 0.5; a < 12.0; a += 1.5) {
        for (double b = 0.5; b < 12.0; b += 1.5) {
            double x = 0.37;
            SK_CLOSE(sk_betai(a, b, x) + sk_betai(b, a, 1.0 - x), 1.0, 1e-12);
        }
    }

    /* Endpoints and domain. */
    SK_CLOSE(sk_betai(2.0, 3.0, 0.0), 0.0, 1e-15);
    SK_CLOSE(sk_betai(2.0, 3.0, 1.0), 1.0, 1e-15);
    SK_CHECK(isnan(sk_betai(2.0, 3.0, -0.1)));
    SK_CHECK(isnan(sk_betai(2.0, 3.0, 1.1)));
    SK_CHECK(isnan(sk_betai(0.0, 3.0, 0.5)));
    SK_CHECK(isnan(sk_betai(2.0, -1.0, 0.5)));

    /* Known reference value. */
    SK_CLOSE(sk_betai(2.5, 4.0, 0.3), 0.3521975859067672, 1e-9);

    SK_DONE();
}
