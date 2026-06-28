#include "k9_mac.h"

#include <openssl/evp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int decode_payload_b64(const char *in, uint8_t *out, size_t *out_len) {
    size_t len = strlen(in);
    char *tmp = malloc(len + 4);
    if (!tmp) {
        return -1;
    }
    strcpy(tmp, in);
    size_t pad = (4 - (len % 4)) % 4;
    for (size_t i = 0; i < pad; i++) {
        tmp[len + i] = '=';
    }
    tmp[len + pad] = '\0';
    for (size_t i = 0; tmp[i]; i++) {
        if (tmp[i] == '-') {
            tmp[i] = '+';
        } else if (tmp[i] == '_') {
            tmp[i] = '/';
        }
    }
    int decoded = EVP_DecodeBlock(out, (const unsigned char *)tmp, (int)(len + pad));
    free(tmp);
    if (decoded < 0) {
        return -2;
    }
    if (pad > 0) {
        decoded -= (int)pad;
    }
    *out_len = (size_t)decoded;
    return 0;
}

static int assemble_mac_string(const char *header, const char *payload,
                               char *out, size_t cap, size_t *out_len) {
    if (!header || !payload || !out || !out_len) {
        return -1;
    }
    if (header[0] == '\0' || payload[0] == '\0') {
        return -1;
    }
    int written = snprintf(out, cap, "%s%s", header, payload);
    if (written < 0 || (size_t)written >= cap) {
        return -1;
    }
    *out_len = (size_t)written;
    return 0;
}

int k9_mac_input_from_token(const char *header, const char *payload,
                            char *out, size_t cap, size_t *out_len) {
    (void)decode_payload_b64;
    return assemble_mac_string(header, payload, out, cap, out_len);
}
