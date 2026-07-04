/* Milestone 1 acceptance: regularized incomplete gamma P(a,x), Q(a,x). */
#include "statkit/specfun.h"
#include "runner.h"

int main(void)
{
    printf("test_incgamma\n");

    /* Identity: P(1, x) = 1 - e^{-x}. */
    for (double x = 0.25; x < 12.0; x += 0.5) {
        SK_CLOSE(sk_gammap(1.0, x), 1.0 - exp(-x), 1e-12);
    }

    /* Identity: P(1/2, x) = erf(sqrt(x)). */
    for (double x = 0.1; x < 8.0; x += 0.3) {
        SK_CLOSE(sk_gammap(0.5, x), erf(sqrt(x)), 1e-12);
    }

    /* Complement: P + Q = 1. */
    for (double a = 0.5; a < 30.0; a += 2.0) {
        for (double x = 0.2; x < 40.0; x += 3.0) {
            SK_CLOSE(sk_gammap(a, x) + sk_gammaq(a, x), 1.0, 1e-12);
        }
    }

    /* Boundary and monotonicity. */
    SK_CLOSE(sk_gammap(3.0, 0.0), 0.0, 1e-15);
    SK_CLOSE(sk_gammaq(3.0, 0.0), 1.0, 1e-15);
    SK_CHECK(sk_gammap(4.0, 2.0) < sk_gammap(4.0, 6.0));
    SK_CHECK(sk_gammap(4.0, 6.0) < 1.0 && sk_gammap(4.0, 6.0) > 0.0);

    /* Domain errors return NaN (both P and Q). */
    SK_CHECK(isnan(sk_gammap(-1.0, 2.0)));
    SK_CHECK(isnan(sk_gammap(2.0, -1.0)));
    SK_CHECK(isnan(sk_gammaq(0.0, 2.0)));
    SK_CHECK(isnan(sk_gammaq(2.0, -1.0)));

    SK_DONE();
}
