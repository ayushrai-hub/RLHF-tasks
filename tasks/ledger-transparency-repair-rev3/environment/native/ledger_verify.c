#include "ledger_verify.h"
#include <ctype.h>
#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

/* BUG: uses comma separator and skips memo normalization */
static int parse_csv_fields(const char *csv_row, char fields[6][256]) {
    char buf[2048];
    strncpy(buf, csv_row, sizeof(buf) - 1);
    char *save = NULL;
    char *tok = strtok_r(buf, ",", &save);
    int i = 0;
    while (tok && i < 6) {
        strncpy(fields[i], tok, 255);
        fields[i][255] = '\0';
        tok = strtok_r(NULL, ",", &save);
        i++;
    }
    return i == 6 ? 0 : -1;
}

int ledger_canonicalize_row(const char *csv_row, char *out, size_t out_len) {
    char fields[6][256];
    if (parse_csv_fields(csv_row, fields) != 0) return -1;
    /* BUG: comma join, no memo/time normalization */
    int n = snprintf(out, out_len, "%s,%s,%s,%s,%s,%s",
                     fields[0], fields[1], fields[2], fields[3], fields[4], fields[5]);
    return n > 0 && (size_t)n < out_len ? 0 : -1;
}

static int verify_ed25519(const char *canonical, const char *sig_hex, const char *pub_pem_path) {
    (void)canonical;
    (void)sig_hex;
    (void)pub_pem_path;
    /* BUG: always returns success */
    return 0;
}

static int verify_hmac(const char *canonical, const char *sig_hex) {
    (void)canonical;
    (void)sig_hex;
    return 0;
}

int ledger_verify_signature(
    const char *canonical,
    const char *sig_hex,
    const char *signer,
    const char *posted_at
) {
    (void)posted_at;
    if (strcmp(signer, "legacy-bootstrap") == 0) {
        return verify_hmac(canonical, sig_hex);
    }
    /* BUG: always uses v2 key path regardless of posted_at */
    return verify_ed25519(canonical, sig_hex, "/app/data/keys/ledger-key-v2.pub.pem");
}

int ledger_row_digest(const char *canonical, const char *sig_hex, char *out, size_t out_len) {
    char payload[4096];
    /* BUG: wrong concat order */
    snprintf(payload, sizeof(payload), "%s%s", sig_hex, canonical);
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int digest_len = 0;
    EVP_Digest(payload, strlen(payload), digest, &digest_len, EVP_sha256(), NULL);
    for (unsigned int i = 0; i < digest_len; i++) {
        if (i * 2 + 2 >= out_len) return -1;
        sprintf(out + i * 2, "%02x", digest[i]);
    }
    out[digest_len * 2] = '\0';
    return 0;
}

int ledger_compute_chain_root(const char **row_digests, size_t count, char *root_hex, size_t root_len) {
    /* BUG: wrong genesis seed */
    unsigned char state[EVP_MAX_MD_SIZE];
    unsigned int state_len = 0;
    EVP_Digest("ledger-genesis-v2", 17, state, &state_len, EVP_sha256(), NULL);
    for (size_t i = 0; i < count; i++) {
        char link[128];
        snprintf(link, sizeof(link), "%s%s", (char *)state, row_digests[i]);
        EVP_Digest(link, strlen(link), state, &state_len, EVP_sha256(), NULL);
    }
    for (unsigned int i = 0; i < state_len; i++) {
        if (i * 2 + 2 >= root_len) return -1;
        sprintf(root_hex + i * 2, "%02x", state[i]);
    }
    root_hex[state_len * 2] = '\0';
    return 0;
}
