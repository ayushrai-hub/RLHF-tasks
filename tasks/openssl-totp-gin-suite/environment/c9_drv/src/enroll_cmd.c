#include "k9.h"

#include <stdio.h>
#include <string.h>

int run_enroll_cmd(int argc, char **argv) {
    const char *base_url = K9_BASE_URL_DEFAULT;
    const char *store_dir = NULL;
    const char *handle = NULL;

    for (int i = 0; i < argc; i++) {
        if (strcmp(argv[i], "--base-url") == 0 && i + 1 < argc) {
            base_url = argv[++i];
        } else if (strcmp(argv[i], "--store-dir") == 0 && i + 1 < argc) {
            store_dir = argv[++i];
        } else if (strcmp(argv[i], "--handle") == 0 && i + 1 < argc) {
            handle = argv[++i];
        }
    }
    if (!handle || !store_dir) {
        return 2;
    }
    char account[64];
    int rc = bridge_bind(handle, base_url, store_dir, account, sizeof(account));
    if (rc == 2) {
        return 10;
    }
    if (rc != 0) {
        return 1;
    }
    printf("%s\n", account);
    return 0;
}
