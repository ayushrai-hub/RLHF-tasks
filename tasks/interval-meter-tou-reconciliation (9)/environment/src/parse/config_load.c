#include "parse/config_load.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int load_tariff(const char *path, TariffConfig *tariff) {
    FILE *fp = fopen(path, "r");
    if (!fp) {
        return -1;
    }
    fseek(fp, 0, SEEK_END);
    long sz = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    char *buf = (char *)malloc((size_t)sz + 1);
    if (!buf) {
        fclose(fp);
        return -1;
    }
    fread(buf, 1, (size_t)sz, fp);
    buf[sz] = '\0';
    fclose(fp);

    char *tz = strstr(buf, "\"timezone\"");
    if (tz) {
        char tmp[64];
        if (sscanf(strchr(tz, ':'), ": \"%63[^\"]\"", tmp) == 1) {
            strncpy(tariff->timezone, tmp, sizeof(tariff->timezone) - 1);
        }
    } else {
        strcpy(tariff->timezone, "America/Chicago");
    }

    char *reg = strstr(buf, "\"register_max_kwh\"");
    if (reg) {
        sscanf(strchr(reg, ':'), ": %lf", &tariff->register_max_kwh);
    } else {
        tariff->register_max_kwh = 99999.999;
    }

    char *iv = strstr(buf, "\"interval_minutes\"");
    if (iv) {
        sscanf(strchr(iv, ':'), ": %d", &tariff->interval_minutes);
    } else {
        tariff->interval_minutes = 15;
    }

    char *dw = strstr(buf, "\"demand_window_intervals\"");
    if (dw) {
        sscanf(strchr(dw, ':'), ": %d", &tariff->demand_window_intervals);
    } else {
        tariff->demand_window_intervals = 4;
    }

    free(buf);
    return 0;
}

int load_run_config(const char *path, RunConfig *cfg) {
    memset(cfg, 0, sizeof(*cfg));
    FILE *fp = fopen(path, "r");
    if (!fp) {
        return -1;
    }
    fseek(fp, 0, SEEK_END);
    long sz = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    char *buf = (char *)malloc((size_t)sz + 1);
    if (!buf) {
        fclose(fp);
        return -1;
    }
    fread(buf, 1, (size_t)sz, fp);
    buf[sz] = '\0';
    fclose(fp);

    char *tariff_path = strstr(buf, "\"tariff_path\"");
    char tpath[256] = "/app/environment/config/tariffs.json";
    if (tariff_path) {
        sscanf(strchr(tariff_path, ':'), ": \"%255[^\"]\"", tpath);
    }
    if (load_tariff(tpath, &cfg->tariff) != 0) {
        free(buf);
        return -1;
    }

    const char *cursor = buf;
    cfg->fixture_count = 0;
    while ((cursor = strstr(cursor, "\"name\"")) != NULL && cfg->fixture_count < TOU_MAX_FIXTURES) {
        char name[TOU_ID_LEN] = {0};
        char csv[256] = {0};
        const char *name_colon = strchr(cursor, ':');
        if (!name_colon || sscanf(name_colon, ": \"%31[^\"]\"", name) != 1) {
            cursor += 6;
            continue;
        }
        const char *csv_key = strstr(cursor, "\"csv\"");
        if (!csv_key || csv_key - cursor > 200) {
            cursor += 6;
            continue;
        }
        if (sscanf(strchr(csv_key, ':'), ": \"%255[^\"]\"", csv) != 1) {
            cursor += 6;
            continue;
        }
        strncpy(cfg->fixtures[cfg->fixture_count].name, name, TOU_ID_LEN - 1);
        strncpy(cfg->fixtures[cfg->fixture_count].csv_path, csv, 255);
        cfg->fixture_count += 1;
        cursor += 6;
    }

    free(buf);
    return cfg->fixture_count > 0 ? 0 : -1;
}
