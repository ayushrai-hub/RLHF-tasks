#!/bin/bash
# Oracle solution scoped to milestone 5 only:
# the statctl CLI (.spec parser + driver) handling chi-square GOF, Welch t, and
# one-sample Kolmogorov-Smirnov tests, with Holm correction, critical values,
# and confidence intervals.
set -euo pipefail
cd /app

cat > cli/specparse.c <<'EOF'
#include "specparse.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

typedef struct {
    int     active;
    sk_test t;
    int     n_obs;
    int     n_exp;
    int     have_obs;
    int     have_exp;
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
    if (b->t.kind == SK_TEST_KS_NORMAL) {
        return b->t.ns >= 2 && b->t.have_mu && b->t.have_sigma && b->t.sigma > 0.0;
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
    suite->alpha = 0.05;

    FILE *fp = fopen(path, "r");
    if (!fp) {
        return 1;
    }

    char line[1 << 16];
    block_t blk;
    memset(&blk, 0, sizeof(blk));

    while (fgets(line, sizeof(line), fp)) {
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
            } else if (kind && strcmp(kind, "ks_normal") == 0) {
                blk.t.kind = SK_TEST_KS_NORMAL;
            } else {
                blk.t.kind = SK_TEST_NONE;
            }
        } else if (strcmp(key, "end") == 0) {
            commit(suite, &blk);
        } else if (strcmp(key, "alpha") == 0) {
            char *v = strtok(NULL, " \t\r\n");
            if (v) {
                suite->alpha = strtod(v, NULL);
            }
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
        } else if (strcmp(key, "sample") == 0) {
            blk.t.ns = read_doubles(blk.t.sample, SK_MAX_SAMPLE);
        } else if (strcmp(key, "mu") == 0) {
            char *v = strtok(NULL, " \t\r\n");
            if (v) {
                blk.t.mu = strtod(v, NULL);
                blk.t.have_mu = 1;
            }
        } else if (strcmp(key, "sigma") == 0) {
            char *v = strtok(NULL, " \t\r\n");
            if (v) {
                blk.t.sigma = strtod(v, NULL);
                blk.t.have_sigma = 1;
            }
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
EOF

cat > cli/statctl.c <<'EOF'
#include "specparse.h"

#include "statkit/distrib.h"
#include "statkit/jsonout.h"
#include "statkit/vecstat.h"
#include "statkit/version.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>

typedef struct {
    const sk_test *t;
    const char    *kind;
    double         stat;
    double         df;
    double         pval;
    double         critical;
    double         ci_low;
    double         ci_high;
    double         adj;
    int            reject;
} result_t;

static void ensure_parent_dir(const char *path)
{
    char buf[1024];
    strncpy(buf, path, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';
    for (char *p = buf + 1; *p; ++p) {
        if (*p == '/') {
            *p = '\0';
            mkdir(buf, 0777);
            *p = '/';
        }
    }
}

static int cmp_double(const void *a, const void *b)
{
    double da = *(const double *)a;
    double db = *(const double *)b;
    return (da > db) - (da < db);
}

int main(int argc, char **argv)
{
    const char *spec = NULL;
    const char *out = "/app/output/report.json";

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "-o") == 0 && i + 1 < argc) {
            out = argv[++i];
        } else if (spec == NULL) {
            spec = argv[i];
        }
    }
    if (spec == NULL) {
        fprintf(stderr, "usage: statctl <spec> [-o <out>]\n");
        return 2;
    }

    sk_suite suite;
    if (sk_parse_spec(spec, &suite) != 0) {
        fprintf(stderr, "statctl: cannot open spec '%s'\n", spec);
        return 1;
    }
    if (suite.count == 0) {
        fprintf(stderr, "statctl: no valid tests in '%s'\n", spec);
        sk_suite_free(&suite);
        return 1;
    }

    double alpha = suite.alpha;
    int m = suite.count;
    result_t *res = (result_t *)malloc((size_t)m * sizeof(result_t));

    for (int i = 0; i < m; ++i) {
        const sk_test *t = &suite.tests[i];
        res[i].t = t;
        if (t->kind == SK_TEST_CHISQ_GOF) {
            double s = 0.0;
            for (int c = 0; c < t->n_cat; ++c) {
                double d = t->observed[c] - t->expected[c];
                s += d * d / t->expected[c];
            }
            double df = (double)(t->n_cat - 1 - t->ddof);
            res[i].kind = "chisq_gof";
            res[i].stat = s;
            res[i].df = df;
            res[i].pval = sk_chisq_sf(s, df);
            res[i].critical = sk_chisq_ppf(1.0 - alpha, df);
        } else if (t->kind == SK_TEST_WELCH_T) {
            double ma = sk_mean(t->sample_a, t->na);
            double mb = sk_mean(t->sample_b, t->nb);
            double va = sk_var_unbiased(t->sample_a, t->na);
            double vb = sk_var_unbiased(t->sample_b, t->nb);
            double sa = va / t->na;
            double sb = vb / t->nb;
            double tval = (ma - mb) / sqrt(sa + sb);
            double nu = (sa + sb) * (sa + sb)
                        / (sa * sa / (t->na - 1) + sb * sb / (t->nb - 1));
            res[i].kind = "welch_t";
            res[i].stat = tval;
            res[i].df = nu;
            res[i].pval = 2.0 * (1.0 - sk_tdist_cdf(fabs(tval), nu));
            double se = sqrt(sa + sb);
            double md = ma - mb;
            double tc = sk_tdist_ppf(1.0 - alpha / 2.0, nu);
            res[i].ci_low = md - tc * se;
            res[i].ci_high = md + tc * se;
        } else {
            int n = t->ns;
            double sorted[SK_MAX_SAMPLE];
            memcpy(sorted, t->sample, (size_t)n * sizeof(double));
            qsort(sorted, (size_t)n, sizeof(double), cmp_double);
            double dplus = 0.0;
            double dminus = 0.0;
            for (int k = 0; k < n; ++k) {
                double f = sk_normal_cdf(sorted[k], t->mu, t->sigma);
                double up = (double)(k + 1) / n - f;
                double dn = f - (double)k / n;
                if (up > dplus) {
                    dplus = up;
                }
                if (dn > dminus) {
                    dminus = dn;
                }
            }
            double dstat = dplus > dminus ? dplus : dminus;
            res[i].kind = "ks_normal";
            res[i].stat = dstat;
            res[i].df = 0.0;
            res[i].pval = sk_ks_sf(sqrt((double)n) * dstat);
        }
    }

    int *order = (int *)malloc((size_t)m * sizeof(int));
    for (int i = 0; i < m; ++i) {
        order[i] = i;
    }
    for (int i = 1; i < m; ++i) {
        int key = order[i];
        int j = i - 1;
        while (j >= 0 && res[order[j]].pval > res[key].pval) {
            order[j + 1] = order[j];
            --j;
        }
        order[j + 1] = key;
    }
    double running = 0.0;
    for (int rank = 0; rank < m; ++rank) {
        int idx = order[rank];
        double factor = (double)(m - rank);
        double val = factor * res[idx].pval;
        if (val > 1.0) {
            val = 1.0;
        }
        if (val > running) {
            running = val;
        }
        res[idx].adj = running;
        res[idx].reject = (res[idx].adj <= alpha) ? 1 : 0;
    }

    sk_json j;
    sk_json_init(&j);
    sk_json_raw(&j, "{\"version\":");
    sk_json_number(&j, (double)STATKIT_REPORT_VERSION);
    sk_json_raw(&j, ",\"alpha\":");
    sk_json_number(&j, alpha);
    sk_json_raw(&j, ",\"tests\":[");
    for (int i = 0; i < m; ++i) {
        if (i > 0) {
            sk_json_putc(&j, ',');
        }
        sk_json_raw(&j, "{\"id\":");
        sk_json_string(&j, res[i].t->id);
        sk_json_raw(&j, ",\"kind\":");
        sk_json_string(&j, res[i].kind);
        sk_json_raw(&j, ",\"statistic\":");
        sk_json_number(&j, res[i].stat);
        if (res[i].t->kind != SK_TEST_KS_NORMAL) {
            sk_json_raw(&j, ",\"df\":");
            sk_json_number(&j, res[i].df);
        }
        sk_json_raw(&j, ",\"pvalue\":");
        sk_json_number(&j, res[i].pval);
        sk_json_raw(&j, ",\"adj_pvalue\":");
        sk_json_number(&j, res[i].adj);
        sk_json_raw(&j, ",\"reject\":");
        sk_json_raw(&j, res[i].reject ? "true" : "false");
        if (res[i].t->kind == SK_TEST_CHISQ_GOF) {
            sk_json_raw(&j, ",\"critical_value\":");
            sk_json_number(&j, res[i].critical);
        } else if (res[i].t->kind == SK_TEST_WELCH_T) {
            sk_json_raw(&j, ",\"ci_low\":");
            sk_json_number(&j, res[i].ci_low);
            sk_json_raw(&j, ",\"ci_high\":");
            sk_json_number(&j, res[i].ci_high);
        }
        sk_json_putc(&j, '}');
    }
    sk_json_raw(&j, "]}");

    ensure_parent_dir(out);
    FILE *fp = fopen(out, "w");
    if (!fp) {
        fprintf(stderr, "statctl: cannot write '%s'\n", out);
        sk_json_free(&j);
        free(order);
        free(res);
        sk_suite_free(&suite);
        return 1;
    }
    fputs(j.buf, fp);
    fputc('\n', fp);
    fclose(fp);

    sk_json_free(&j);
    free(order);
    free(res);
    sk_suite_free(&suite);
    return 0;
}
EOF

mkdir -p /app/output
make all
build/statctl data/fixtures/mixed_suite.spec -o /app/output/report.json
cat /app/output/report.json
