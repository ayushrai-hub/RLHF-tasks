#ifndef SFMT_UTF8_H
#define SFMT_UTF8_H

#include <stddef.h>
#include <stdint.h>

size_t sf_utf8_decode(const unsigned char *s, size_t len, uint32_t *cp);

size_t sf_utf8_encode(uint32_t cp, char out[4]);

long sf_utf8_count(const unsigned char *s, size_t len);

int sf_utf8_scalar_valid(uint32_t cp);

#endif
