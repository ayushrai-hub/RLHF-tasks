#include "sfmt/error.h"
#include "sfmt/hexdump.h"
#include "sfmt/level.h"
#include "sfmt/logger.h"
#include "sfmt/record.h"
#include "sfmt/sfmt.h"
#include "sfmt/vec.h"
#include "sfmt/version.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int read_file(const char *path, char *buf, size_t cap, size_t *out_n)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return -1;
    size_t n = fread(buf, 1, cap - 1, f);
    int truncated = !feof(f);
    fclose(f);
    if (truncated)
        return -2;
    buf[n] = 0;
    *out_n = n;
    return 0;
}

static int load_vector(const char *path, sf_vector *v)
{
    static char text[SF_VEC_FMT_CAP + SF_VEC_STR_CAP + 4096];
    size_t n;
    int rc = read_file(path, text, sizeof(text), &n);
    if (rc == -1) {
        fprintf(stderr, "sfmt: cannot open %s\n", path);
        return 2;
    }
    if (rc == -2) {
        fprintf(stderr, "sfmt: vector file too large\n");
        return 2;
    }
    char err[128];
    if (sf_vec_parse(text, n, v, err, sizeof(err)) != 0) {
        fprintf(stderr, "sfmt: %s\n", err);
        return 2;
    }
    return 0;
}

static int emit_result(int rc, const char *out)
{
    if (rc >= 0) {
        fwrite(out, 1, (size_t)rc, stdout);
        return 0;
    }
    const char *tok = sf_error_token(rc);
    fputs(tok ? tok : "@ERR:UNKNOWN", stdout);
    return 1;
}

static int run_fmt(const char *path)
{
    static sf_vector v;
    int rc = load_vector(path, &v);
    if (rc)
        return rc;
    static char out[65536];
    return emit_result(sf_format(v.fmt, v.args, v.nargs, out, sizeof(out)), out);
}

static int run_log(const char *level_s, const char *path)
{
    sf_level level;
    if (sf_level_parse(level_s, &level) != 0) {
        fprintf(stderr, "sfmt: unknown level %s\n", level_s);
        return 2;
    }
    static sf_vector v;
    int rc = load_vector(path, &v);
    if (rc)
        return rc;
    sf_sink sink;
    sf_sink_init_file(&sink, stdout);
    sf_logger lg;
    sf_logger_init(&lg, sink, SF_LEVEL_DEBUG);
    sf_record r = {level, v.fmt, v.args, v.nargs};
    int er = sf_logger_emit(&lg, &r);
    if (er < 0) {
        fputs(sf_error_token(er) ? sf_error_token(er) : "@ERR:UNKNOWN", stdout);
        return 1;
    }
    return 0;
}

static int run_hexdump(const char *path)
{
    static char data[65536];
    size_t n;
    int rc = read_file(path, data, sizeof(data), &n);
    if (rc != 0) {
        fprintf(stderr, "sfmt: cannot read %s\n", path);
        return 2;
    }
    static char out[262144];
    return emit_result(
        sf_hexdump((const unsigned char *)data, n, out, sizeof(out)), out);
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "version") == 0) {
        printf("sfmt %s\n", sf_version_string());
        return 0;
    }
    if (argc == 3 && strcmp(argv[1], "fmt") == 0)
        return run_fmt(argv[2]);
    if (argc == 4 && strcmp(argv[1], "log") == 0)
        return run_log(argv[2], argv[3]);
    if (argc == 3 && strcmp(argv[1], "hexdump") == 0)
        return run_hexdump(argv[2]);

    fprintf(stderr, "usage: sfmt fmt <vector-file>\n");
    fprintf(stderr, "       sfmt log <debug|info|warn|error> <vector-file>\n");
    fprintf(stderr, "       sfmt hexdump <file>\n");
    fprintf(stderr, "       sfmt version\n");
    return 2;
}
