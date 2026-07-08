#ifndef SFMT_SFMT_H
#define SFMT_SFMT_H

#include <stddef.h>
#include <stdint.h>

typedef enum {
    SF_ARG_I64,
    SF_ARG_U64,
    SF_ARG_STR,
    SF_ARG_BYTE,
    SF_ARG_SCALAR
} sf_argtype;

typedef struct {
    sf_argtype type;
    int64_t i64;
    uint64_t u64;
    const char *str;
    size_t slen;
} sf_arg;

enum {
    SF_OK = 0,
    SF_ERR_NOT_IMPLEMENTED = -1,
    SF_ERR_BAD_SPEC = -2,
    SF_ERR_MIX = -3,
    SF_ERR_ARG_COUNT = -4,
    SF_ERR_ARG_TYPE = -5,
    SF_ERR_PERCENT_N = -6,
    SF_ERR_BAD_UTF8 = -7,
    SF_ERR_BAD_SCALAR = -8,
    SF_ERR_NOMEM = -9
};

int sf_format(const char *fmt, const sf_arg *args, size_t nargs,
              char *out, size_t outcap);

#endif
