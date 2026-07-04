#ifndef STATKIT_RUNNER_H
#define STATKIT_RUNNER_H

/*
 * Minimal assertion harness for the statkit acceptance tests. Each test file
 * defines main(), runs a sequence of checks, and ends with SK_DONE(). A test
 * binary exits 0 only if every check passed.
 *
 * These files are the frozen acceptance suite. Do not weaken or delete the
 * checks; implement the library so they pass.
 */

#include <math.h>
#include <stdio.h>

static int sk__fail = 0;

#define SK_CHECK(cond)                                                       \
    do {                                                                     \
        if (!(cond)) {                                                       \
            printf("  FAIL: %s (line %d)\n", #cond, __LINE__);               \
            sk__fail = 1;                                                    \
        }                                                                    \
    } while (0)

#define SK_CLOSE(a, b, tol)                                                  \
    do {                                                                     \
        double sk__a = (a), sk__b = (b), sk__t = (tol);                      \
        if (!(fabs(sk__a - sk__b) <= sk__t)) {                               \
            printf("  FAIL: |%.17g - %.17g| > %.3g (line %d)\n",             \
                   sk__a, sk__b, sk__t, __LINE__);                           \
            sk__fail = 1;                                                    \
        }                                                                    \
    } while (0)

#define SK_DONE()                                                            \
    do {                                                                     \
        if (sk__fail) {                                                      \
            printf("RESULT: FAIL\n");                                        \
            return 1;                                                        \
        }                                                                    \
        printf("RESULT: PASS\n");                                            \
        return 0;                                                            \
    } while (0)

#endif /* STATKIT_RUNNER_H */
