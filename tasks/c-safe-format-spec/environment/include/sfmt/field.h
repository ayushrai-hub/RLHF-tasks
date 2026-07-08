#ifndef SFMT_FIELD_H
#define SFMT_FIELD_H

#include "sfmt/sfmt.h"

typedef struct {
    const char *key;
    sf_arg val;
} sf_field;

int sf_field_render(const sf_field *f, char *out, size_t cap);

#endif
