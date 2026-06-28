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
    unsigned int lane = (unsigned int)(digest[digest_len - 2] & 0x0f);
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
