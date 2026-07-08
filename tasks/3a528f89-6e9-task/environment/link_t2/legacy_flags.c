#include <stdint.h>
#include <stdio.h>
#include <string.h>

int pack_t2(const char *spec_path, uint8_t flags, char *out_path, size_t olen);

int legacy_flags_stamp(const char *spec_path, char *out_path, size_t olen)
{
    if (!spec_path || !out_path) {
        return -1;
    }
    snprintf(out_path, olen, "/tmp/legacy_%s", spec_path);
    return 0;
}
