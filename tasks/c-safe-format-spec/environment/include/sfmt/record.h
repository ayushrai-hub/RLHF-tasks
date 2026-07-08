#ifndef SFMT_RECORD_H
#define SFMT_RECORD_H

#include "sfmt/level.h"
#include "sfmt/sfmt.h"

typedef struct {
    sf_level level;
    const char *fmt;
    const sf_arg *args;
    size_t nargs;
} sf_record;

int sf_record_render(const sf_record *r, char *out, size_t cap);

#endif
