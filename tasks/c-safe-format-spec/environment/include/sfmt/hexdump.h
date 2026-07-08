#ifndef SFMT_HEXDUMP_H
#define SFMT_HEXDUMP_H

#include <stddef.h>

int sf_hexdump(const unsigned char *data, size_t n, char *out, size_t cap);

#endif
