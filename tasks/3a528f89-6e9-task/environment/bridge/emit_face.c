#include <stddef.h>

int emit_z4(const void *rows, size_t n, const char *out_json, const char *chain_stamp);

int emit_face_write(const void *rows, size_t n, const char *out_json, const char *chain_stamp)
{
    return emit_z4(rows, n, out_json, chain_stamp);
}
