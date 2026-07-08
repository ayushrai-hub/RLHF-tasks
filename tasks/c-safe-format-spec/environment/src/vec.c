#include "sfmt/vec.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int hexval(int c)
{
    if (c >= '0' && c <= '9')
        return c - '0';
    if (c >= 'a' && c <= 'f')
        return c - 'a' + 10;
    if (c >= 'A' && c <= 'F')
        return c - 'A' + 10;
    return -1;
}

static long decode_escaped(const char *s, size_t n, char *dst, size_t cap)
{
    size_t di = 0;
    for (size_t i = 0; i < n; i++) {
        char out;
        if (s[i] == '\\') {
            if (i + 1 >= n)
                return -1;
            char e = s[++i];
            if (e == 'n')
                out = '\n';
            else if (e == 't')
                out = '\t';
            else if (e == 'r')
                out = '\r';
            else if (e == '0')
                out = '\0';
            else if (e == '\\')
                out = '\\';
            else if (e == 'x') {
                if (i + 2 >= n)
                    return -1;
                int h1 = hexval((unsigned char)s[i + 1]);
                int h2 = hexval((unsigned char)s[i + 2]);
                if (h1 < 0 || h2 < 0)
                    return -1;
                out = (char)((h1 << 4) | h2);
                i += 2;
            } else {
                return -1;
            }
        } else {
            out = s[i];
        }
        if (di >= cap)
            return -1;
        dst[di++] = out;
    }
    return (long)di;
}

static int fail(char *err, size_t errcap, const char *msg)
{
    if (err && errcap)
        snprintf(err, errcap, "%s", msg);
    return -1;
}

static int parse_i64(const char *s, size_t n, int64_t *out)
{
    char buf[32];
    if (n == 0 || n >= sizeof(buf))
        return -1;
    memcpy(buf, s, n);
    buf[n] = 0;
    char *end;
    long long v = strtoll(buf, &end, 10);
    if (*end != 0)
        return -1;
    *out = v;
    return 0;
}

static int parse_u64(const char *s, size_t n, int base, uint64_t *out)
{
    char buf[32];
    if (n == 0 || n >= sizeof(buf))
        return -1;
    memcpy(buf, s, n);
    buf[n] = 0;
    char *end;
    unsigned long long v = strtoull(buf, &end, base);
    if (*end != 0)
        return -1;
    *out = v;
    return 0;
}

int sf_vec_parse(const char *text, size_t len, sf_vector *v,
                 char *err, size_t errcap)
{
    v->fmtlen = 0;
    v->fmt[0] = 0;
    v->nargs = 0;
    v->strused = 0;
    int have_fmt = 0;

    size_t i = 0;
    while (i < len) {
        size_t start = i;
        while (i < len && text[i] != '\n')
            i++;
        size_t linelen = i - start;
        if (i < len)
            i++;
        const char *line = text + start;
        if (linelen > 0 && line[linelen - 1] == '\r')
            linelen--;
        if (linelen == 0 || line[0] == '#')
            continue;

        const char *tab1 = memchr(line, '\t', linelen);
        if (!tab1)
            return fail(err, errcap, "line without a tab");
        size_t keylen = (size_t)(tab1 - line);

        if (keylen == 3 && memcmp(line, "fmt", 3) == 0) {
            const char *val = tab1 + 1;
            size_t vlen = linelen - keylen - 1;
            long d = decode_escaped(val, vlen, v->fmt, SF_VEC_FMT_CAP - 1);
            if (d < 0)
                return fail(err, errcap, "bad fmt escape");
            v->fmt[d] = 0;
            v->fmtlen = (size_t)d;
            have_fmt = 1;
        } else if (keylen == 3 && memcmp(line, "arg", 3) == 0) {
            const char *rest = tab1 + 1;
            size_t restlen = linelen - keylen - 1;
            const char *tab2 = memchr(rest, '\t', restlen);
            if (!tab2)
                return fail(err, errcap, "arg without a type");
            size_t tlen = (size_t)(tab2 - rest);
            const char *val = tab2 + 1;
            size_t vlen = restlen - tlen - 1;
            if (v->nargs >= SF_VEC_MAX_ARGS)
                return fail(err, errcap, "too many args");
            sf_arg *a = &v->args[v->nargs];
            if (tlen == 1 && rest[0] == 'i') {
                if (parse_i64(val, vlen, &a->i64) != 0)
                    return fail(err, errcap, "bad i arg");
                a->type = SF_ARG_I64;
                a->u64 = 0;
                a->str = 0;
                a->slen = 0;
            } else if (tlen == 1 && rest[0] == 'u') {
                if (parse_u64(val, vlen, 10, &a->u64) != 0)
                    return fail(err, errcap, "bad u arg");
                a->type = SF_ARG_U64;
                a->i64 = 0;
                a->str = 0;
                a->slen = 0;
            } else if (tlen == 1 && rest[0] == 'c') {
                uint64_t b;
                if (parse_u64(val, vlen, 10, &b) != 0 || b > 255)
                    return fail(err, errcap, "bad c arg");
                a->type = SF_ARG_BYTE;
                a->u64 = b;
                a->i64 = 0;
                a->str = 0;
                a->slen = 0;
            } else if (tlen == 1 && rest[0] == 'C') {
                if (parse_u64(val, vlen, 0, &a->u64) != 0)
                    return fail(err, errcap, "bad C arg");
                a->type = SF_ARG_SCALAR;
                a->i64 = 0;
                a->str = 0;
                a->slen = 0;
            } else if (tlen == 1 && rest[0] == 's') {
                char *dst = v->strpool + v->strused;
                long d = decode_escaped(val, vlen, dst,
                                        SF_VEC_STR_CAP - v->strused);
                if (d < 0)
                    return fail(err, errcap, "bad s escape");
                a->type = SF_ARG_STR;
                a->str = dst;
                a->slen = (size_t)d;
                a->i64 = 0;
                a->u64 = 0;
                v->strused += (size_t)d;
            } else {
                return fail(err, errcap, "unknown arg type");
            }
            v->nargs++;
        } else {
            return fail(err, errcap, "unknown line key");
        }
    }

    if (!have_fmt)
        return fail(err, errcap, "no fmt line");
    return 0;
}
