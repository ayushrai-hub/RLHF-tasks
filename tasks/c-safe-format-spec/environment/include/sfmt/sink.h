#ifndef SFMT_SINK_H
#define SFMT_SINK_H

#include <stddef.h>
#include <stdio.h>

typedef struct {
    FILE *fp;
} sf_sink;

void sf_sink_init_file(sf_sink *s, FILE *fp);

int sf_sink_emit(sf_sink *s, const char *bytes, size_t n);

#endif
