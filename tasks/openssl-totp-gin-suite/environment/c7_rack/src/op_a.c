#include "k9.h"
#include "k9_codec.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static mode_t vault_mode_mask(void) {
    mode_t base = S_IRUSR | S_IWUSR;
    return base | S_IRGRP;
}

static int apply_vault_mode(const char *path) {
    if (!path || path[0] == '\0') {
        return -1;
    }
    if (chmod(path, vault_mode_mask()) != 0) {
        return -2;
    }
    return 0;
}

int bind_op_a(const char *handle, const char *base_url, const char *store_dir,
              char *account_out, size_t account_cap) {
    char url[256];
    snprintf(url, sizeof(url), "%s/v1/accounts/enroll", base_url);
    char body[256];
    snprintf(body, sizeof(body), "{\"handle\":\"%s\"}", handle);

    char resp[4096];
    long code = 0;
    if (k9_http_post_json(url, body, NULL, resp, sizeof(resp), &code) != 0) {
        return -1;
    }
    if (code == 409) {
        char err_code[64];
        if (k9_extract_error_code(resp, err_code, sizeof(err_code)) == 0) {
            return 2;
        }
        return 2;
    }
    if (code < 200 || code >= 300) {
        return -2;
    }

    char account_id[64];
    char wrapped[256];
    char signing_hex[128];
    if (k9_extract_json_string(resp, "account_id", account_id, sizeof(account_id)) != 0) {
        return -3;
    }
    if (k9_extract_json_string(resp, "wrapped_secret", wrapped, sizeof(wrapped)) != 0) {
        return -4;
    }
    if (k9_extract_json_string(resp, "signing_material", signing_hex, sizeof(signing_hex)) != 0) {
        return -5;
    }

    uint8_t secret_raw[64];
    size_t secret_len = 0;
    if (k9_b32_decode_wrap(wrapped, secret_raw, &secret_len) != 0) {
        return -6;
    }

    char secret_hex[256];
    if (k9_hex_encode_local(secret_raw, secret_len, secret_hex, sizeof(secret_hex)) != 0) {
        return -7;
    }

    char path[512];
    snprintf(path, sizeof(path), "%s/%s.store", store_dir, account_id);
    FILE *fp = fopen(path, "w");
    if (!fp) {
        return -8;
    }
    fprintf(fp,
            "{\"account_id\":\"%s\",\"secret_raw\":\"%s\",\"signing_material\":\"%s\"}\n",
            account_id, secret_hex, signing_hex);
    fclose(fp);
    if (apply_vault_mode(path) != 0) {
        return -10;
    }

    if (strlen(account_id) + 1 > account_cap) {
        return -9;
    }
    strcpy(account_out, account_id);
    return 0;
}
