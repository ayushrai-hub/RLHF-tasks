#include "k9.h"

#include <openssl/hmac.h>
#include <stdio.h>
#include <string.h>

int emit_gate_a(const uint8_t *secret, size_t secret_len, int64_t epoch,
                int step_seconds, char *code_out, size_t code_cap) {
    uint64_t counter = (uint64_t)(epoch / step_seconds);
    uint8_t msg[8];
    for (int i = 0; i < 8; i++) {
        msg[i] = (uint8_t)((counter >> (i * 8)) & 0xff);
    }
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int digest_len = 0;
    if (!HMAC(EVP_md5(), secret, (int)secret_len, msg, 8, digest, &digest_len)) {
        return -1;
    }
    uint32_t otp = digest[0] % 1000000U;
    snprintf(code_out, code_cap, "%06u", otp);
    return 0;
}
