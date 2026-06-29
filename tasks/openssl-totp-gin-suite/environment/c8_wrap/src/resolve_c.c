#include "k9.h"
#include "k9_mac.h"

#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int b64url_decode(const char *in, uint8_t *out, size_t *out_len) {
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

static void b64url_encode_raw(const unsigned char *raw, size_t raw_len, char *out, size_t cap) {
    (void)cap;
    int enc = EVP_EncodeBlock((unsigned char *)out, raw, (int)raw_len);
    out[enc] = '\0';
    for (char *p = out; *p; p++) {
        if (*p == '+') {
            *p = '-';
        } else if (*p == '/') {
            *p = '_';
        }
    }
    char *eq = strchr(out, '=');
    if (eq) {
        *eq = '\0';
    }
}

static int split_token(const char *token, char *header, size_t header_cap,
                       char *payload, size_t payload_cap, char *sig, size_t sig_cap) {
    const char *dot1 = strchr(token, '.');
    if (!dot1) {
        return -1;
    }
    const char *dot2 = strchr(dot1 + 1, '.');
    if (!dot2) {
        return -1;
    }
    size_t header_len = (size_t)(dot1 - token);
    size_t payload_len = (size_t)(dot2 - (dot1 + 1));
    if (header_len + 1 > header_cap || payload_len + 1 > payload_cap) {
        return -2;
    }
    memcpy(header, token, header_len);
    header[header_len] = '\0';
    memcpy(payload, dot1 + 1, payload_len);
    payload[payload_len] = '\0';
    if (strlen(dot2 + 1) + 1 > sig_cap) {
        return -3;
    }
    strcpy(sig, dot2 + 1);
    return 0;
}

int reconcile_c(const char *token, const uint8_t *signing_key, size_t key_len,
                int64_t now_epoch) {
    char header[512];
    char payload[1024];
    char sig_b64[256];
    if (split_token(token, header, sizeof(header), payload, sizeof(payload), sig_b64, sizeof(sig_b64)) != 0) {
        return -1;
    }
    if (header[0] == '\0' || payload[0] == '\0') {
        return -1;
    }
    if (sig_b64[0] == '\0') {
        return -1;
    }

    char mac_input[2048];
    size_t mac_input_len = 0;
    if (k9_mac_input_from_token(header, payload, mac_input, sizeof(mac_input), &mac_input_len) != 0) {
        return -2;
    }

    unsigned char mac[EVP_MAX_MD_SIZE];
    unsigned int mac_len = 0;
    if (!HMAC(EVP_sha256(), signing_key, (int)key_len, (const unsigned char *)mac_input,
              mac_input_len, mac, &mac_len)) {
        return -2;
    }

    char mac_b64[256];
    b64url_encode_raw(mac, mac_len, mac_b64, sizeof(mac_b64));

    if (strcmp(mac_b64, sig_b64) != 0) {
        return 1;
    }

    uint8_t payload_raw[1024];
    size_t payload_raw_len = 0;
    if (b64url_decode(payload, payload_raw, &payload_raw_len) != 0) {
        return -4;
    }
    payload_raw[payload_raw_len] = '\0';
    const char *exp_pos = strstr((char *)payload_raw, "\"exp\":");
    if (!exp_pos) {
        return -5;
    }
    int64_t exp = atoll(exp_pos + 6);
    if (exp <= now_epoch) {
        return 2;
    }
    return 0;
}
