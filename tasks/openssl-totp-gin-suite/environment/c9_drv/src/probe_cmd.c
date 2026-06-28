#include "k9.h"
#include "k9_step.h"
#include "k9_store.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int run_probe_cmd(int argc, char **argv) {
    const char *store_dir = NULL;
    const char *account_id = NULL;
    int64_t clock_epoch = 0;

    for (int i = 0; i < argc; i++) {
        if (strcmp(argv[i], "--store-dir") == 0 && i + 1 < argc) {
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
    if (clock_epoch <= 0) {
        const char *host = getenv("K9_CLOCK_EPOCH");
        if (host && host[0]) {
            clock_epoch = atoll(host);
        }
    }
    if (clock_epoch <= 0) {
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
    printf("%s\n", code);
    return 0;
}
