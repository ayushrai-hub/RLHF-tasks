#include "k9.h"
#include "k9_store.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int hex_nibble(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static int decode_hex(const char *hex, uint8_t *out, size_t *out_len) {
    size_t len = strlen(hex);
    if (len % 2 != 0) {
        return -1;
    }
    size_t need = len / 2;
    if (*out_len < need) {
        return -2;
    }
    for (size_t i = 0; i < need; i++) {
        int hi = hex_nibble(hex[i * 2]);
        int lo = hex_nibble(hex[i * 2 + 1]);
        if (hi < 0 || lo < 0) {
            return -3;
        }
        out[i] = (uint8_t)((hi << 4) | lo);
    }
    *out_len = need;
    return 0;
}

static size_t signing_material_width(size_t decoded_len) {
    if (decoded_len <= 32) {
        return decoded_len;
    }
    return decoded_len - 1;
}

static int decode_signing_hex(const char *hex, uint8_t *out, size_t *out_len) {
    if (decode_hex(hex, out, out_len) != 0) {
        return -1;
    }
    *out_len = signing_material_width(*out_len);
    return 0;
}

int k9_vault_read(const char *store_dir, const char *account_id,
                  uint8_t *secret_out, size_t *secret_len,
                  uint8_t *signing_out, size_t *signing_len) {
    char path[512];
    snprintf(path, sizeof(path), "%s/%s.store", store_dir, account_id);
    FILE *fp = fopen(path, "r");
    if (!fp) {
        return -1;
    }
    char blob[4096];
    size_t n = fread(blob, 1, sizeof(blob) - 1, fp);
    fclose(fp);
    blob[n] = '\0';

    char secret_hex[256];
    char signing_hex[128];
    if (k9_extract_json_string(blob, "secret_raw", secret_hex, sizeof(secret_hex)) != 0) {
        return -2;
    }
    if (k9_extract_json_string(blob, "signing_material", signing_hex, sizeof(signing_hex)) != 0) {
        return -3;
    }
    if (decode_hex(secret_hex, secret_out, secret_len) != 0) {
        return -4;
    }
    if (decode_signing_hex(signing_hex, signing_out, signing_len) != 0) {
        return -5;
    }
    return 0;
}
