#include "sfmt/writer.h"

void sf_writer_init(sf_writer *w, char *buf, size_t cap)
{
    w->buf = buf;
    w->cap = cap;
    w->len = 0;
    w->overflow = 0;
}

int sf_writer_put(sf_writer *w, char c)
{
    if (w->len >= w->cap) {
        w->overflow = 1;
        return -1;
    }
    w->buf[w->len++] = c;
    return 0;
}

int sf_writer_write(sf_writer *w, const char *p, size_t n)
{
    if (n > w->cap - w->len) {
        w->overflow = 1;
        return -1;
    }
    for (size_t i = 0; i < n; i++)
        w->buf[w->len++] = p[i];
    return 0;
}

int sf_writer_fill(sf_writer *w, char c, size_t n)
{
    if (n > w->cap - w->len) {
        w->overflow = 1;
        return -1;
    }
    for (size_t i = 0; i < n; i++)
        w->buf[w->len++] = c;
    return 0;
}
