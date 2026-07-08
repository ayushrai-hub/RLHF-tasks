#ifndef LEDGER_VERIFY_H
#define LEDGER_VERIFY_H

#include <stddef.h>

int ledger_canonicalize_row(const char *csv_row, char *out, size_t out_len);
int ledger_verify_signature(
    const char *canonical,
    const char *sig_hex,
    const char *signer,
    const char *posted_at
);
int ledger_row_digest(const char *canonical, const char *sig_hex, char *out, size_t out_len);
int ledger_compute_chain_root(const char **row_digests, size_t count, char *root_hex, size_t root_len);

#endif
