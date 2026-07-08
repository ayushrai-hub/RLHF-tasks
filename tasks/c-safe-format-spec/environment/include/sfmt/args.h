#ifndef SFMT_ARGS_H
#define SFMT_ARGS_H

#include "sfmt/sfmt.h"

sf_arg sf_i64(int64_t v);
sf_arg sf_u64(uint64_t v);
sf_arg sf_str(const char *s, size_t n);
sf_arg sf_byte(unsigned v);
sf_arg sf_scalar(uint32_t v);

#endif
