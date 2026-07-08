#include <stddef.h>
#include <stdint.h>

int op_r8(const uint8_t *note, size_t nlen, const char *interp_path, uint32_t *out_flags);

int stage_load_merge(const uint8_t *note, size_t nlen, const char *path_token, uint32_t *out_flags)
{
    return op_r8(note, nlen, path_token, out_flags);
}
