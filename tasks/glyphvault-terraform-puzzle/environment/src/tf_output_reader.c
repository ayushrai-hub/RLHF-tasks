#define _POSIX_C_SOURCE 200809L

#include "glyphvault/tf_output_reader.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* BROKEN: reads deprecated tile_px output key instead of tile_size */
int gv_read_tile_size(const char *terraform_dir, int *tile_size_out) {
    if (!terraform_dir || !tile_size_out) return -1;
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "terraform -chdir=%s output -raw tile_px 2>/dev/null", terraform_dir);
    FILE *fp = popen(cmd, "r");
    if (!fp) return -1;
    char buf[64] = {0};
    if (!fgets(buf, sizeof(buf), fp)) {
        pclose(fp);
        return -1;
    }
    pclose(fp);
    *tile_size_out = atoi(buf);
    if (*tile_size_out <= 0) *tile_size_out = 16;
    return 0;
}
