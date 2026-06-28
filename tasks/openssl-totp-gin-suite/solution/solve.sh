#!/bin/bash
set -euo pipefail

# Enrollment persistence files must not grant group or other permission bits.
sed -i 's/return base | S_IRGRP;/return base;/' /app/environment/c7_rack/src/op_a.c

# Base32 padding octets terminate the decode stream.
sed -i 's/continue;/break;/' /app/environment/c7_rack/src/op_a_support.c

# Duplicate enrollment conflicts must surface from the bind bridge unchanged.
sed -i 's/return 0;/return rc;/' /app/environment/c9_drv/src/bind_bridge.c

# Dual-epoch blending must use step_seconds from driver policy, not step_window.
cat > /app/environment/pkt_vend/src/lane_blend.c <<'EOF'
#include "k9_lane.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int read_toml_int(const char *path, const char *key, int fallback) {
    FILE *fp = fopen(path, "r");
    if (!fp) {
        return fallback;
    }
    char line[256];
    char pattern[64];
    snprintf(pattern, sizeof(pattern), "%s =", key);
    size_t plen = strlen(pattern);
    int found = fallback;
    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, pattern, plen) != 0) {
            continue;
        }
        const char *eq = strchr(line, '=');
        if (!eq) {
            continue;
        }
        found = atoi(eq + 1);
        break;
    }
    fclose(fp);
    return found;
}

static int host_step_width(void) {
    int seconds = read_toml_int("/app/environment/c9_drv/config/driver.toml", "step_seconds", 30);
    return seconds > 0 ? seconds : 30;
}

int64_t lane_blend_epochs(int64_t host_epoch, int64_t material_epoch) {
    int width = host_step_width();
    if (host_epoch == material_epoch) {
        return material_epoch;
    }
    int64_t delta = host_epoch - material_epoch;
    int64_t steps = delta / width;
    if (steps >= -1 && steps <= 1) {
        return host_epoch;
    }
    return material_epoch;
}
EOF

# Passcode epoch binding must read K9_PASSCODE_EPOCH, not the host clock override.
cat > /app/environment/pkt_vend/src/lane_sync.c <<'EOF'
#include "k9_lane.h"

#include <stdlib.h>

extern int64_t lane_blend_epochs(int64_t host_epoch, int64_t material_epoch);

int64_t lane_pick_material_epoch(int64_t host_epoch) {
    const char *bound = getenv("K9_PASSCODE_EPOCH");
    if (!bound || !bound[0]) {
        return host_epoch;
    }
    return lane_blend_epochs(host_epoch, atoll(bound));
}
EOF

# Stride must stay at configured step width even when passcode epoch binding is active.
cat > /app/environment/pkt_vend/src/step_bridge.c <<'EOF'
#include "k9.h"
#include "k9_step.h"

extern int emit_gate_b(const uint8_t *secret, size_t secret_len, int64_t epoch,
                       int step_seconds, int window, char *code_out, size_t code_cap);

static int effective_stride(int step_seconds, int window) {
    (void)window;
    return step_seconds;
}

int bridge_step(const uint8_t *secret, size_t secret_len, int64_t epoch,
                int step_seconds, int window, char *code_out, size_t code_cap) {
    int stride = effective_stride(step_seconds, window);
    return emit_gate_b(secret, secret_len, epoch, stride, window, code_out, code_cap);
}
EOF

# Dynamic truncation reads the low nibble of the final digest byte.
cat > /app/environment/pkt_vend/src/emit_b.c <<'EOF'
#include "k9.h"
#include "k9_counter.h"
#include "k9_lane.h"

#include <openssl/hmac.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int pick_truncation_offset(const unsigned char *digest, unsigned int digest_len) {
    if (digest_len < 20) {
        return 0;
    }
    unsigned int lane = (unsigned int)(digest[digest_len - 1] & 0x0f);
    if (lane + 3 >= digest_len) {
        lane = 0;
    }
    if (lane + 3 >= digest_len) {
        return 0;
    }
    return (int)lane;
}

static uint32_t dynamic_slice(const unsigned char *digest, int offset) {
    return ((uint32_t)(digest[offset] & 0x7f) << 24) |
           ((uint32_t)digest[offset + 1] << 16) |
           ((uint32_t)digest[offset + 2] << 8) |
           (uint32_t)digest[offset + 3];
}

int emit_gate_b(const uint8_t *secret, size_t secret_len, int64_t epoch,
                int step_seconds, int window, char *code_out, size_t code_cap) {
    (void)window;
    if (code_cap < 8) {
        return -1;
    }
    if (!secret || secret_len == 0) {
        return -1;
    }
    int64_t material_epoch = lane_pick_material_epoch(epoch);
    uint64_t counter = (uint64_t)(material_epoch / step_seconds);
    uint8_t msg[8];
    k9_pack_counter_be(counter, msg);

    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int digest_len = 0;
    if (!HMAC(EVP_sha1(), secret, (int)secret_len, msg, 8, digest, &digest_len)) {
        return -2;
    }
    if (digest_len < 20) {
        return -2;
    }

    int offset = pick_truncation_offset(digest, digest_len);
    if (offset + 3 >= (int)digest_len) {
        return -2;
    }
    uint32_t bin_code = dynamic_slice(digest, offset);
    uint32_t otp = bin_code % 1000000U;
    snprintf(code_out, code_cap, "%06u", otp);
    return 0;
}
EOF

# Session MAC input is the dotted header and payload segments.
cat > /app/environment/c8_wrap/src/mac_segment.c <<'EOF'
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
    int written = snprintf(out, cap, "%s.%s", header, payload);
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
EOF

# Signing key material must load at full decoded width for verification.
cat > /app/environment/c9_drv/src/vault_io.c <<'EOF'
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
    return decoded_len;
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
EOF

cat > /app/environment/pkt_vend/src/counter_pack.c <<'EOF'
#include "k9_counter.h"

void k9_pack_counter_be(uint64_t counter, uint8_t out[8]) {
    for (int i = 0; i < 8; i++) {
        out[i] = (uint8_t)((counter >> (56 - i * 8)) & 0xff);
    }
}
EOF

cat > /app/environment/c8_wrap/src/seal_bridge.c <<'EOF'
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
    if (!strchr(split + 1, '.')) {
        return NULL;
    }
    return token;
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
EOF

/app/environment/scripts/build_m3.sh
/app/environment/scripts/grad_driver.sh --session-out /app/output/run_ledger.json
