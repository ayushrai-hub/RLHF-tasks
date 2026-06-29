#include "k9.h"
#include "k9_seal.h"
#include "k9_store.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int run_verify_cmd(int argc, char **argv) {
    const char *store_dir = NULL;
    const char *account_id = NULL;
    const char *token = NULL;
    int64_t clock_epoch = 0;

    for (int i = 0; i < argc; i++) {
        if (strcmp(argv[i], "--store-dir") == 0 && i + 1 < argc) {
            store_dir = argv[++i];
        } else if (strcmp(argv[i], "--account-id") == 0 && i + 1 < argc) {
            account_id = argv[++i];
        } else if (strcmp(argv[i], "--token") == 0 && i + 1 < argc) {
            token = argv[++i];
        } else if (strcmp(argv[i], "--clock-epoch") == 0 && i + 1 < argc) {
            clock_epoch = atoll(argv[++i]);
        }
    }
    if (!account_id || !token || !store_dir) {
        return 2;
    }
    uint8_t secret[64];
    size_t secret_len = sizeof(secret);
    uint8_t signing[64];
    size_t signing_len = sizeof(signing);
    if (k9_vault_read(store_dir, account_id, secret, &secret_len, signing, &signing_len) != 0) {
        return 1;
    }
    (void)secret;
    int rc = bridge_route_gate(token, signing, signing_len, clock_epoch);
    if (rc == 1 || rc == 2) {
        return 12;
    }
    if (rc != 0) {
        return 1;
    }
    printf("verified\n");
    return 0;
}
