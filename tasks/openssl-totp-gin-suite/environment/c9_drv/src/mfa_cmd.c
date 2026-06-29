#include "k9.h"
#include "k9_step.h"
#include "k9_store.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int run_mfa_cmd(int argc, char **argv) {
    const char *base_url = K9_BASE_URL_DEFAULT;
    const char *store_dir = NULL;
    const char *account_id = NULL;
    int64_t clock_epoch = 0;

    for (int i = 0; i < argc; i++) {
        if (strcmp(argv[i], "--base-url") == 0 && i + 1 < argc) {
            base_url = argv[++i];
        } else if (strcmp(argv[i], "--store-dir") == 0 && i + 1 < argc) {
            store_dir = argv[++i];
        } else if (strcmp(argv[i], "--account-id") == 0 && i + 1 < argc) {
            account_id = argv[++i];
        } else if (strcmp(argv[i], "--clock-epoch") == 0 && i + 1 < argc) {
            clock_epoch = atoll(argv[++i]);
        }
    }
    if (!account_id || !store_dir) {
        return 2;
    }
    uint8_t secret[64];
    size_t secret_len = sizeof(secret);
    uint8_t signing[64];
    size_t signing_len = sizeof(signing);
    if (k9_vault_read(store_dir, account_id, secret, &secret_len, signing, &signing_len) != 0) {
        return 1;
    }
    (void)signing;
    char code[16];
    if (bridge_step(secret, secret_len, clock_epoch, K9_STEP_SECONDS, K9_STEP_WINDOW, code, sizeof(code)) != 0) {
        return 1;
    }
    char url[256];
    snprintf(url, sizeof(url), "%s/v1/sessions/mfa", base_url);
    char body[512];
    snprintf(body, sizeof(body), "{\"account_id\":\"%s\",\"passcode\":\"%s\"}", account_id, code);
    char hdr[64];
    snprintf(hdr, sizeof(hdr), "X-Clock-Epoch: %lld", (long long)clock_epoch);
    char resp[4096];
    long http_code = 0;
    if (k9_http_post_json(url, body, hdr, resp, sizeof(resp), &http_code) != 0) {
        return 1;
    }
    if (http_code == 401) {
        return 11;
    }
    if (http_code < 200 || http_code >= 300) {
        return 1;
    }
    char token_out[2048];
    if (k9_extract_json_string(resp, "session_token", token_out, sizeof(token_out)) != 0) {
        return 1;
    }
    printf("%s\n", token_out);
    return 0;
}
