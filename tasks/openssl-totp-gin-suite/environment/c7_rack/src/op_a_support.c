#include "k9.h"

#include <string.h>

static const char *B32_ALPH = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

static int b32_value(char c) {
    const char *p = strchr(B32_ALPH, c);
    if (!p) {
        if (c == '=') {
            return 0;
        }
        return -1;
    }
    return (int)(p - B32_ALPH);
}

int k9_b32_decode_wrap(const char *in, uint8_t *out, size_t *out_len) {
    size_t o = 0;
    int buffer = 0;
    int bits = 0;
    for (size_t i = 0; in[i]; i++) {
        char c = in[i];
        if (c == '=') {
            continue;
        }
        int v = b32_value(c);
        if (v < 0) {
            return -1;
        }
        buffer = (buffer << 5) | v;
        bits += 5;
        if (bits >= 8) {
            bits -= 8;
            out[o++] = (uint8_t)((buffer >> bits) & 0xff);
        }
    }
    *out_len = o;
    return 0;
}

int k9_hex_encode_local(const uint8_t *raw, size_t len, char *out, size_t cap) {
    if (cap < len * 2 + 1) {
        return -1;
    }
    static const char *hex = "0123456789abcdef";
    for (size_t i = 0; i < len; i++) {
        out[i * 2] = hex[(raw[i] >> 4) & 0xf];
        out[i * 2 + 1] = hex[raw[i] & 0xf];
    }
    out[len * 2] = '\0';
    return 0;
}
