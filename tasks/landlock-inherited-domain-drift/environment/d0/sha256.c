#include "../lib/sha256.h"

void d0_sha256_hex_prefix(const uint8_t *data, size_t len, size_t n_hex, char *out)
{
    sha256_hex_prefix(data, len, n_hex, out);
}
