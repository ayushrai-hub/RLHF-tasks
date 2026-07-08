#ifndef SFMT_WRITER_H
#define SFMT_WRITER_H

#include <stddef.h>

typedef struct {
    char *buf;
    size_t cap;
    size_t len;
    int overflow;
} sf_writer;

void sf_writer_init(sf_writer *w, char *buf, size_t cap);

int sf_writer_put(sf_writer *w, char c);

int sf_writer_write(sf_writer *w, const char *p, size_t n);

int sf_writer_fill(sf_writer *w, char c, size_t n);

#endif
