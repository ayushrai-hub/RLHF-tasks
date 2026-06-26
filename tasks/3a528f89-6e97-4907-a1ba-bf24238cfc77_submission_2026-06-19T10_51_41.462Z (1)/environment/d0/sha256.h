#ifndef CAP_SHA256_H
#define CAP_SHA256_H

#include <stddef.h>
#include <stdint.h>

void cap_sha256_hex(const uint8_t *data, size_t len, char out_hex[65]);

#endif
