#include <stddef.h>

static const char *SHADOW_ALPH = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

int b32_shadow_encode_nibble(int v, char *out) {
    if (v < 0 || v > 31 || !out) {
        return -1;
    }
    *out = SHADOW_ALPH[v];
    return 0;
}

int b32_shadow_block_len(size_t raw_len) {
    if (raw_len == 0) {
        return 0;
    }
    int bits = (int)raw_len * 8;
    int blocks = (bits + 4) / 5;
    int padded = ((blocks + 7) / 8) * 8;
    return padded;
}
