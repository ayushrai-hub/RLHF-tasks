#include "specparse.h"

#include "statkit/distrib.h"
#include "statkit/jsonout.h"
#include "statkit/vecstat.h"
#include "statkit/version.h"

#include <math.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>

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

static void chisq_gof(const sk_test *t, double *stat, double *df, double *pval)
{
    double s = 0.0;
    for (int i = 0; i < t->n_cat; ++i) {
        double d = t->observed[i] - t->expected[i];
        s += d * d / t->expected[i];
    }
    *stat = s;
    *df = (double)(t->n_cat - 1 - t->ddof);
    *pval = sk_chisq_sf(s, *df);
}

static void welch_t(const sk_test *t, double *stat, double *df, double *pval)
{
    double ma = sk_mean(t->sample_a, t->na);
    double mb = sk_mean(t->sample_b, t->nb);
    double va = sk_var_unbiased(t->sample_a, t->na);
    double vb = sk_var_unbiased(t->sample_b, t->nb);
    double sa = va / t->na;
    double sb = vb / t->nb;
    double tval = (ma - mb) / sqrt(sa + sb);
    double nu = (sa + sb) * (sa + sb)
                / (sa * sa / (t->na - 1) + sb * sb / (t->nb - 1));
    double p = 2.0 * (1.0 - sk_tdist_cdf(fabs(tval), nu));
    *stat = tval;
    *df = nu;
    *pval = p;
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

    sk_json j;
    sk_json_init(&j);
    sk_json_raw(&j, "{\"version\":");
    sk_json_number(&j, (double)STATKIT_REPORT_VERSION);
    sk_json_raw(&j, ",\"tests\":[");
    for (int i = 0; i < suite.count; ++i) {
        const sk_test *t = &suite.tests[i];
        double stat = 0.0, df = 0.0, pval = 0.0;
        const char *kind = "";
        if (t->kind == SK_TEST_CHISQ_GOF) {
            chisq_gof(t, &stat, &df, &pval);
            kind = "chisq_gof";
        } else if (t->kind == SK_TEST_WELCH_T) {
            welch_t(t, &stat, &df, &pval);
            kind = "welch_t";
        }
        if (i > 0) {
            sk_json_putc(&j, ',');
        }
        sk_json_raw(&j, "{\"id\":");
        sk_json_string(&j, t->id);
        sk_json_raw(&j, ",\"kind\":");
        sk_json_string(&j, kind);
        sk_json_raw(&j, ",\"statistic\":");
        sk_json_number(&j, stat);
        sk_json_raw(&j, ",\"df\":");
        sk_json_number(&j, df);
        sk_json_raw(&j, ",\"pvalue\":");
        sk_json_number(&j, pval);
        sk_json_putc(&j, '}');
    }
    sk_json_raw(&j, "]}");

    ensure_parent_dir(out);
    FILE *fp = fopen(out, "w");
    if (!fp) {
        fprintf(stderr, "statctl: cannot write '%s'\n", out);
        sk_json_free(&j);
        sk_suite_free(&suite);
        return 1;
    }
    fputs(j.buf, fp);
    fputc('\n', fp);
    fclose(fp);

    sk_json_free(&j);
    sk_suite_free(&suite);
    return 0;
}
