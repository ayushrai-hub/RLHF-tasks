#include "parse_core.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int parse_kv_file(const char *path, const char *key, char *out, size_t out_len)
{
    FILE *fp = fopen(path, "r");
    if (fp == NULL || out == NULL || out_len == 0) {
        return -1;
    }
    char line[256];
    while (fgets(line, sizeof(line), fp) != NULL) {
        char *eq = strchr(line, '=');
        if (eq == NULL) {
            continue;
        }
        *eq = '\0';
        char *val = eq + 1;
        val[strcspn(val, "\r\n")] = '\0';
        if (strcmp(line, key) == 0) {
            (void)snprintf(out, out_len, "%s", val);
            fclose(fp);
            return 0;
        }
    }
    fclose(fp);
    return -1;
}

int parse_hex_kv(const char *path, const char *key, uint32_t *value)
{
    char buf[64];
    if (value == NULL || parse_kv_file(path, key, buf, sizeof(buf)) != 0) {
        return -1;
    }
    *value = (uint32_t)strtoul(buf, NULL, 0);
    return 0;
}

int parse_auth_tag(const char *table_path, const char *mark, int *tag_out)
{
    FILE *fp = fopen(table_path, "r");
    if (fp == NULL || mark == NULL || tag_out == NULL) {
        return -1;
    }
    char line[256];
    while (fgets(line, sizeof(line), fp) != NULL) {
        char m[64];
        int tag = 0;
        if (sscanf(line, "%63s\t%d", m, &tag) < 2) {
            continue;
        }
        if (strcmp(m, mark) == 0) {
            *tag_out = tag;
            fclose(fp);
            return 0;
        }
    }
    fclose(fp);
    return -1;
}
