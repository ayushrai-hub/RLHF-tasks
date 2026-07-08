#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int parse_link_tag(const char *spec_path, int *out_tag)
{
    FILE *fp = fopen(spec_path, "r");
    if (!fp || !out_tag) {
        return -1;
    }
    char line[128];
    int in_main = 0;
    int tag = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "[main]")) {
            in_main = 1;
            continue;
        }
        if (strstr(line, "[dep]")) {
            in_main = 0;
            continue;
        }
        if (in_main && strstr(line, "link_tag")) {
            if (sscanf(line, " link_tag = %d", &tag) == 1) {
                fclose(fp);
                *out_tag = tag;
                return 0;
            }
        }
    }
    fclose(fp);
    return -2;
}

int pack_t2(const char *spec_path, uint8_t flags, char *out_path, size_t olen)
{
    if (!spec_path || !out_path || olen < 64) {
        return -1;
    }
    char slot[64];
    if (sscanf(spec_path, "/app/environment/fixtures/spec_t2/%63s", slot) != 1) {
        return -2;
    }
    int link_tag = 0;
    if (parse_link_tag(spec_path, &link_tag) != 0) {
        return -3;
    }
    uint8_t emit = flags ? (uint8_t)link_tag : 0;
    snprintf(out_path, olen, "/tmp/link_out_%s_tag%u", slot, (unsigned)emit);
    return 0;
}
