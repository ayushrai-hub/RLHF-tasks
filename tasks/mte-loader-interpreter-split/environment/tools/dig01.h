#ifndef DIG01_H
#define DIG01_H

#include <stddef.h>
#include <stdint.h>

uint64_t dig01_fnv1a64(const uint8_t *data, size_t len);
int dig01_note_bytes(const char *path, uint8_t *out, size_t *olen);
int dig01_digest_hex(const char *path, char *hex, size_t hlen);

#endif
