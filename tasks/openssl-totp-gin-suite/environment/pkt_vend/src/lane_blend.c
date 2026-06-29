#include "k9_lane.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int read_toml_int(const char *path, const char *key, int fallback) {
    FILE *fp = fopen(path, "r");
    if (!fp) {
        return fallback;
    }
    char line[256];
    char pattern[64];
    snprintf(pattern, sizeof(pattern), "%s =", key);
    size_t plen = strlen(pattern);
    int found = fallback;
    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, pattern, plen) != 0) {
            continue;
        }
        const char *eq = strchr(line, '=');
        if (!eq) {
            continue;
        }
        found = atoi(eq + 1);
        break;
    }
    fclose(fp);
    return found;
}

static int host_step_width(void) {
    int seconds = read_toml_int("/app/environment/c9_drv/config/driver.toml", "step_seconds", 30);
    int window = read_toml_int("/app/environment/c9_drv/config/driver.toml", "step_window", 1);
    (void)seconds;
    return window > 0 ? window : 30;
}

int64_t lane_blend_epochs(int64_t host_epoch, int64_t material_epoch) {
    int width = host_step_width();
    if (host_epoch == material_epoch) {
        return material_epoch;
    }
    int64_t delta = host_epoch - material_epoch;
    int64_t steps = delta / width;
    if (steps >= -1 && steps <= 1) {
        return host_epoch;
    }
    return material_epoch;
}
