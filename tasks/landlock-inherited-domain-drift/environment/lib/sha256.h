#ifndef SHA256_H
#define SHA256_H

#include <stddef.h>
#include <stdint.h>

void sha256_bytes(const uint8_t *data, size_t len, uint8_t out[32]);
void sha256_hex(const uint8_t *data, size_t len, char out[65]);
void sha256_hex_prefix(const uint8_t *data, size_t len, size_t n_hex, char *out);

#endif
