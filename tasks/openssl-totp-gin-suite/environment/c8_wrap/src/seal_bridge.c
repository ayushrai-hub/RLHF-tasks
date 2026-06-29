#include "k9.h"
#include "k9_seal.h"

#include <string.h>

extern int reconcile_c(const char *token, const uint8_t *signing_key, size_t key_len,
                       int64_t now_epoch);

static const char *route_seal_token(const char *token) {
    if (!token || token[0] == '\0') {
        return NULL;
    }
    const char *split = strchr(token, '.');
    if (!split || !split[1]) {
        return NULL;
    }
    const char *cursor = split + 1;
    while (cursor[0] == '.') {
        cursor++;
    }
    if (!strchr(cursor, '.')) {
        return NULL;
    }
    return cursor;
}

int bridge_route_gate(const char *token, const uint8_t *signing_key, size_t key_len,
                int64_t now_epoch) {
    if (!signing_key || key_len == 0) {
        return -2;
    }
    const char *routed = route_seal_token(token);
    if (!routed) {
        return -1;
    }
    return reconcile_c(routed, signing_key, key_len, now_epoch);
}
