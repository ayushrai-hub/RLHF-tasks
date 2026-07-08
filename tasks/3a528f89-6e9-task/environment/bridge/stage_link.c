#include <stddef.h>
#include <stdint.h>

int pack_t2(const char *spec_path, uint8_t flags, char *out_path, size_t olen);

int stage_link_emit(const char *spec_path, uint8_t flags, char *out_path, size_t olen)
{
    return pack_t2(spec_path, flags, out_path, olen);
}
