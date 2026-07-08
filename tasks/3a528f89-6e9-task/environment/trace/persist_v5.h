#ifndef PERSIST_V5_H
#define PERSIST_V5_H

#include <stdint.h>

int persist_reset(const char *path);
int persist_seal_decoy(const char *path, uint32_t decoy_viol);
int persist_seal_walk(const char *path, uint32_t walk_viol, int asym);
int persist_viol_for_profile(const char *path, const char *profile, uint32_t *out_viol);

#endif
