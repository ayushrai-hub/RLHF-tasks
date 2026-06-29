#ifndef K9_SEAL_H
#define K9_SEAL_H

#include <stddef.h>
#include <stdint.h>

int bridge_route_gate(const char *token, const uint8_t *signing_key, size_t key_len,
                int64_t now_epoch);

#endif
