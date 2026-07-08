#include "chain_io.h"
#include "dig01.h"

#include <stdio.h>
#include <string.h>

int chain_reset(const char *path)
{
    if (!path) {
        return -1;
    }
    FILE *fp = fopen(path, "w");
    if (!fp) {
        return -2;
    }
    fclose(fp);
    return 0;
}

int chain_append(
    const char *path,
    const char *profile,
    unsigned violations,
    int asym,
    unsigned fault_obs,
    const char *lineage_col)
{
    if (!path || !profile || !lineage_col) {
        return -1;
    }
    FILE *fp = fopen(path, "a");
    if (!fp) {
        return -2;
    }
    fprintf(
        fp,
        "%s\t%u\t%d\t%u\t%s\n",
        profile,
        violations,
        asym,
        fault_obs,
        lineage_col);
    fclose(fp);
    return 0;
}

int chain_stamp_hex(const char *path, char *out, size_t olen)
{
    if (!path || !out || olen < 17) {
        return -1;
    }
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        return -2;
    }
    unsigned char buf[512];
    size_t n = fread(buf, 1, sizeof(buf), fp);
    fclose(fp);
    uint64_t h = dig01_fnv1a64(buf, n);
    snprintf(out, olen, "%016llx", (unsigned long long)(h & 0xffffffffffffULL));
    return 0;
}
