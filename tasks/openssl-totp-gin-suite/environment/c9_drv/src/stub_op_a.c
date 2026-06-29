#include "k9.h"

#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

int stub_op_a_handle_ok(const char *handle) {
    if (!handle || !handle[0]) {
        return 0;
    }
    for (const char *p = handle; *p; p++) {
        if (!isalnum((unsigned char)*p) && *p != '_' && *p != '-') {
            return 0;
        }
    }
    return 1;
}

int stub_op_a_wrap_len_ok(const char *wrapped) {
    if (!wrapped) {
        return 0;
    }
    size_t n = 0;
    for (const char *p = wrapped; *p; p++) {
        n++;
    }
    return n >= 8;
}

int stub_op_a_store_draft(const char *handle, const char *store_dir, const char *wrapped,
                          const char *account_id) {
    if (!stub_op_a_handle_ok(handle) || !stub_op_a_wrap_len_ok(wrapped)) {
        return -1;
    }
    char path[512];
    snprintf(path, sizeof(path), "%s/%s.store", store_dir, account_id);
    FILE *fp = fopen(path, "w");
    if (!fp) {
        return -2;
    }
    fprintf(fp,
            "{\"account_id\":\"%s\",\"secret_raw\":\"%s\",\"signing_material\":\"%s\"}\n",
            account_id, wrapped, wrapped);
    fclose(fp);
    chmod(path, 0600);
    return 0;
}
