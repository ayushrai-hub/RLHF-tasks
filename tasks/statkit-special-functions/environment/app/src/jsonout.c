#include "statkit/jsonout.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void sk_json_init(sk_json *j)
{
    j->cap = 256;
    j->len = 0;
    j->buf = (char *)malloc(j->cap);
    if (j->buf) {
        j->buf[0] = '\0';
    }
}

void sk_json_free(sk_json *j)
{
    free(j->buf);
    j->buf = NULL;
    j->len = 0;
    j->cap = 0;
}

static void sk_json__reserve(sk_json *j, size_t extra)
{
    if (j->len + extra + 1 <= j->cap) {
        return;
    }
    while (j->len + extra + 1 > j->cap) {
        j->cap *= 2;
    }
    j->buf = (char *)realloc(j->buf, j->cap);
}

void sk_json_putc(sk_json *j, char c)
{
    sk_json__reserve(j, 1);
    j->buf[j->len++] = c;
    j->buf[j->len] = '\0';
}

void sk_json_raw(sk_json *j, const char *s)
{
    size_t n = strlen(s);
    sk_json__reserve(j, n);
    memcpy(j->buf + j->len, s, n);
    j->len += n;
    j->buf[j->len] = '\0';
}

void sk_json_string(sk_json *j, const char *s)
{
    sk_json_putc(j, '"');
    for (const char *p = s; *p; ++p) {
        unsigned char c = (unsigned char)*p;
        if (c == '"' || c == '\\') {
            sk_json_putc(j, '\\');
            sk_json_putc(j, (char)c);
        } else if (c == '\n') {
            sk_json_raw(j, "\\n");
        } else if (c == '\t') {
            sk_json_raw(j, "\\t");
        } else if (c < 0x20) {
            char tmp[8];
            snprintf(tmp, sizeof(tmp), "\\u%04x", c);
            sk_json_raw(j, tmp);
        } else {
            sk_json_putc(j, (char)c);
        }
    }
    sk_json_putc(j, '"');
}

void sk_json_number(sk_json *j, double v)
{
    char tmp[64];
    snprintf(tmp, sizeof(tmp), "%.10g", v);
    sk_json_raw(j, tmp);
}
