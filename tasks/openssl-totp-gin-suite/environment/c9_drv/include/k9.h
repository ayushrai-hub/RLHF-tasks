#ifndef K9_H
#define K9_H

#include <stddef.h>
#include <stdint.h>

#define K9_BASE_URL_DEFAULT "http://127.0.0.1:9477"
#define K9_STEP_SECONDS 30
#define K9_STEP_WINDOW 1
#define K9_DIGITS 6

int k9_http_post_json(const char *url, const char *body, const char *extra_hdr,
                      char *resp, size_t resp_cap, long *http_code);

int bridge_bind(const char *handle, const char *base_url, const char *store_dir,
                char *account_out, size_t account_cap);

int k9_extract_json_string(const char *json, const char *key, char *out, size_t out_cap);

int k9_extract_error_code(const char *json, char *out, size_t out_cap);

int run_enroll_cmd(int argc, char **argv);
int run_mfa_cmd(int argc, char **argv);
int run_verify_cmd(int argc, char **argv);
int run_probe_cmd(int argc, char **argv);

#endif
