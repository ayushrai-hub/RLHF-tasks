#ifndef SFMT_VEC_H
#define SFMT_VEC_H

#include "sfmt/sfmt.h"

#define SF_VEC_FMT_CAP 8192
#define SF_VEC_STR_CAP 16384
#define SF_VEC_MAX_ARGS 64

typedef struct {
    char fmt[SF_VEC_FMT_CAP];
    size_t fmtlen;
    sf_arg args[SF_VEC_MAX_ARGS];
    size_t nargs;
    char strpool[SF_VEC_STR_CAP];
    size_t strused;
} sf_vector;

int sf_vec_parse(const char *text, size_t len, sf_vector *v,
                 char *err, size_t errcap);

#endif
