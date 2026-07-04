#include "specparse.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Grow the suite by one slot and return a pointer to it (zero-initialized). */
static sk_test *suite_push(sk_suite *suite)
{
    sk_test *grown = (sk_test *)realloc(
        suite->tests, (size_t)(suite->count + 1) * sizeof(sk_test));
    if (!grown) {
        return NULL;
    }
    suite->tests = grown;
    sk_test *t = &suite->tests[suite->count];
    memset(t, 0, sizeof(*t));
    return t;
}

/* Parsing state for the block currently being read. */
typedef struct {
    int          active;
    sk_test      t;
    int          n_obs;
    int          n_exp;
    int          have_obs;
    int          have_exp;
} block_t;

static int validate(const block_t *b)
{
    if (b->t.kind == SK_TEST_CHISQ_GOF) {
        if (!b->have_obs || !b->have_exp) {
            return 0;
        }
        if (b->n_obs != b->n_exp || b->n_obs < 1) {
            return 0;
        }
        for (int i = 0; i < b->n_exp; ++i) {
            if (!(b->t.expected[i] > 0.0)) {
                return 0;
            }
        }
        return 1;
    }
    if (b->t.kind == SK_TEST_WELCH_T) {
        return b->t.na >= 2 && b->t.nb >= 2;
    }
    return 0;
}

static void commit(sk_suite *suite, block_t *b)
{
    if (b->active && validate(b)) {
        sk_test *slot = suite_push(suite);
        if (slot) {
            b->t.n_cat = b->n_obs;
            *slot = b->t;
            suite->count += 1;
        }
    }
    memset(b, 0, sizeof(*b));
}

static int read_doubles(double *dst, int cap)
{
    int n = 0;
    char *tok;
    while ((tok = strtok(NULL, " \t\r\n")) != NULL && n < cap) {
        dst[n++] = strtod(tok, NULL);
    }
    return n;
}

int sk_parse_spec(const char *path, sk_suite *suite)
{
    suite->tests = NULL;
    suite->count = 0;

    FILE *fp = fopen(path, "r");
    if (!fp) {
        return 1;
    }

    char line[1 << 16];
    block_t blk;
    memset(&blk, 0, sizeof(blk));

    while (fgets(line, sizeof(line), fp)) {
        /* Skip blank lines and comments (first non-space char is '#'). */
        const char *p = line;
        while (*p == ' ' || *p == '\t') {
            ++p;
        }
        if (*p == '\0' || *p == '\n' || *p == '\r' || *p == '#') {
            continue;
        }

        char work[1 << 16];
        strncpy(work, line, sizeof(work) - 1);
        work[sizeof(work) - 1] = '\0';

        char *key = strtok(work, " \t\r\n");
        if (!key) {
            continue;
        }

        if (strcmp(key, "test") == 0) {
            commit(suite, &blk);
            char *id = strtok(NULL, " \t\r\n");
            char *kind = strtok(NULL, " \t\r\n");
            blk.active = 1;
            if (id) {
                strncpy(blk.t.id, id, SK_MAX_ID - 1);
            }
            if (kind && strcmp(kind, "chisq_gof") == 0) {
                blk.t.kind = SK_TEST_CHISQ_GOF;
            } else if (kind && strcmp(kind, "welch_t") == 0) {
                blk.t.kind = SK_TEST_WELCH_T;
            } else {
                blk.t.kind = SK_TEST_NONE;
            }
        } else if (strcmp(key, "end") == 0) {
            commit(suite, &blk);
        } else if (!blk.active) {
            continue;
        } else if (strcmp(key, "observed") == 0) {
            blk.n_obs = read_doubles(blk.t.observed, SK_MAX_CATEGORIES);
            blk.have_obs = 1;
        } else if (strcmp(key, "expected") == 0) {
            blk.n_exp = read_doubles(blk.t.expected, SK_MAX_CATEGORIES);
            blk.have_exp = 1;
        } else if (strcmp(key, "ddof") == 0) {
            char *v = strtok(NULL, " \t\r\n");
            blk.t.ddof = v ? atoi(v) : 0;
        } else if (strcmp(key, "sample_a") == 0) {
            blk.t.na = read_doubles(blk.t.sample_a, SK_MAX_SAMPLE);
        } else if (strcmp(key, "sample_b") == 0) {
            blk.t.nb = read_doubles(blk.t.sample_b, SK_MAX_SAMPLE);
        }
    }
    commit(suite, &blk);

    fclose(fp);
    return 0;
}

void sk_suite_free(sk_suite *suite)
{
    free(suite->tests);
    suite->tests = NULL;
    suite->count = 0;
}
