#ifndef CHAIN_IO_H
#define CHAIN_IO_H

#include <stddef.h>

int chain_reset(const char *path);
int chain_append(
    const char *path,
    const char *profile,
    unsigned violations,
    int asym,
    unsigned fault_obs,
    const char *lineage_col);
int chain_stamp_hex(const char *path, char *out, size_t olen);

#endif
