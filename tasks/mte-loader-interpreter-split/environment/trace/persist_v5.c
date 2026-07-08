#include "persist_v5.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    uint32_t decoy_viol;
    uint32_t walk_viol;
    int asym;
} persist_blob;

int persist_reset(const char *path)
{
    if (!path) {
        return -1;
    }
    FILE *fp = fopen(path, "wb");
    if (!fp) {
        return -2;
    }
    persist_blob z = {0, 0, 0};
    if (fwrite(&z, sizeof(z), 1, fp) != 1) {
        fclose(fp);
        return -3;
    }
    fclose(fp);
    return 0;
}

static int persist_load(const char *path, persist_blob *out)
{
    FILE *fp = fopen(path, "rb");
    if (!fp) {
        return -1;
    }
    if (fread(out, sizeof(*out), 1, fp) != 1) {
        fclose(fp);
        return -2;
    }
    fclose(fp);
    return 0;
}

static int persist_store(const char *path, const persist_blob *blob)
{
    FILE *fp = fopen(path, "wb");
    if (!fp) {
        return -1;
    }
    if (fwrite(blob, sizeof(*blob), 1, fp) != 1) {
        fclose(fp);
        return -2;
    }
    fclose(fp);
    return 0;
}

int persist_seal_decoy(const char *path, uint32_t decoy_viol)
{
    persist_blob blob;
    if (persist_load(path, &blob) != 0) {
        return -1;
    }
    blob.decoy_viol = decoy_viol;
    return persist_store(path, &blob);
}

int persist_seal_walk(const char *path, uint32_t walk_viol, int asym)
{
    persist_blob blob;
    if (persist_load(path, &blob) != 0) {
        return -1;
    }
    blob.walk_viol = walk_viol;
    blob.asym = asym;
    return persist_store(path, &blob);
}

int persist_viol_for_profile(const char *path, const char *profile, uint32_t *out_viol)
{
    if (!path || !profile || !out_viol) {
        return -1;
    }
    persist_blob blob;
    if (persist_load(path, &blob) != 0) {
        return -2;
    }
    if (strcmp(profile, "fw_a") == 0) {
        *out_viol = blob.decoy_viol;
        return 0;
    }
    *out_viol = blob.walk_viol;
    return 0;
}
