#ifndef K9_STEP_H
#define K9_STEP_H

#include <stddef.h>
#include <stdint.h>

int bridge_step(const uint8_t *secret, size_t secret_len, int64_t epoch,
                int step_seconds, int window, char *code_out, size_t code_cap);

#endif
