#ifndef K9_CODEC_H
#define K9_CODEC_H

#include <stddef.h>
#include <stdint.h>

int k9_b32_decode_wrap(const char *in, uint8_t *out, size_t *out_len);

int k9_hex_encode_local(const uint8_t *raw, size_t len, char *out, size_t cap);

#endif
