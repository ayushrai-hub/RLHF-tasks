#ifndef STATKIT_SPECPARSE_H
#define STATKIT_SPECPARSE_H

#include <stddef.h>

/*
 * In-memory model of a .spec test suite (see docs/FORMAT.md for the on-disk
 * grammar). The parser is part of milestone 3; this header only fixes the data
 * model shared between the parser and statctl. You may extend it as needed, but
 * statctl's emitted report must match docs/FORMAT.md.
 */

#define SK_MAX_CATEGORIES 256
#define SK_MAX_SAMPLE     1024
#define SK_MAX_ID         64

typedef enum {
    SK_TEST_NONE = 0,
    SK_TEST_CHISQ_GOF,
    SK_TEST_WELCH_T,
    SK_TEST_KS_NORMAL
} sk_test_kind;

typedef struct {
    sk_test_kind kind;
    char id[SK_MAX_ID];

    /* chisq_gof */
    double observed[SK_MAX_CATEGORIES];
    double expected[SK_MAX_CATEGORIES];
    int    n_cat;
    int    ddof;

    /* welch_t */
    double sample_a[SK_MAX_SAMPLE];
    double sample_b[SK_MAX_SAMPLE];
    int    na;
    int    nb;

    /* ks_normal */
    double sample[SK_MAX_SAMPLE];
    int    ns;
    double mu;
    double sigma;
    int    have_mu;
    int    have_sigma;
} sk_test;

typedef struct {
    sk_test *tests;
    int      count;
    double   alpha;   /* suite significance level; default 0.05 */
} sk_suite;

/*
 * Parse the .spec file at `path` into `suite`. Returns 0 on success (file
 * readable), non-zero if the file cannot be opened. Individual malformed test
 * blocks are handled per docs/FORMAT.md rather than failing the whole parse.
 */
int sk_parse_spec(const char *path, sk_suite *suite);

void sk_suite_free(sk_suite *suite);

#endif /* STATKIT_SPECPARSE_H */
