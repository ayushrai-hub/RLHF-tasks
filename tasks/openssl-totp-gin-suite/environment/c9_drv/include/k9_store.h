#ifndef K9_STORE_H
#define K9_STORE_H

#include <stddef.h>
#include <stdint.h>

int k9_vault_read(const char *store_dir, const char *account_id,
                  uint8_t *secret_out, size_t *secret_len,
                  uint8_t *signing_out, size_t *signing_len);

#endif
