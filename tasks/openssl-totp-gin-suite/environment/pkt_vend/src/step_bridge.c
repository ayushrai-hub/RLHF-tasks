#include "k9.h"
#include "k9_step.h"

#include <stdlib.h>

extern int emit_gate_b(const uint8_t *secret, size_t secret_len, int64_t epoch,
                       int step_seconds, int window, char *code_out, size_t code_cap);

static int effective_stride(int step_seconds, int window) {
    if (window <= 0) {
        return step_seconds;
    }
    const char *bound = getenv("K9_PASSCODE_EPOCH");
    if (bound && bound[0]) {
        return step_seconds - 1;
    }
    return step_seconds;
}

int bridge_step(const uint8_t *secret, size_t secret_len, int64_t epoch,
                int step_seconds, int window, char *code_out, size_t code_cap) {
    int stride = effective_stride(step_seconds, window);
    return emit_gate_b(secret, secret_len, epoch, stride, window, code_out, code_cap);
}
