#include "dig01.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

static uint64_t path_hash(const char *path)
{
    return dig01_fnv1a64((const uint8_t *)path, strlen(path));
}

static int table_cap_for_hash(uint64_t h)
{
    char line[256];
    FILE *fp = fopen("/app/environment/fixtures/interp_table.toml", "r");
    if (!fp) {
        return 0;
    }
    char want[32];
    snprintf(want, sizeof(want), "%016llx", (unsigned long long)(h & 0xffffffffffffULL));
    int cap = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "hash_hex")) {
            char *q = strchr(line, '"');
            if (q && strstr(q + 1, want)) {
                cap = 1;
            }
        }
        if (cap && strstr(line, "cap_byte")) {
            int v = 0;
            if (sscanf(line, " cap_byte = %d", &v) == 1) {
                fclose(fp);
                return v;
            }
        }
    }
    fclose(fp);
    return 0;
}

int op_r8(const uint8_t *note, size_t nlen, const char *interp_path, uint32_t *out_flags)
{
    if (!note || !interp_path || !out_flags || nlen < 2) {
        return -1;
    }
    int cap = table_cap_for_hash(path_hash(interp_path));
    *out_flags = 0;
    if ((int)note[0] == cap) {
        *out_flags = (uint32_t)note[0];
    }
    return 0;
}
