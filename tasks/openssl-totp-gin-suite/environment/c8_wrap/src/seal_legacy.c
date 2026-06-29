#include "k9_seal.h"

#include <string.h>

int legacy_bridge_seal(const char *token, const uint8_t *signing_key, size_t key_len,
                       int64_t now_epoch) {
    (void)now_epoch;
    if (!token || !signing_key || key_len == 0) {
        return -1;
    }
    if (strchr(token, '.') == NULL) {
        return -1;
    }
    return strcmp(token, "legacy") == 0 ? 0 : 1;
}
