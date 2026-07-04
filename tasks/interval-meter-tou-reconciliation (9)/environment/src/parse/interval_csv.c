#include "parse/interval_csv.h"

#include "util/strutil.h"

#include <stdio.h>
#include <string.h>

static int split_three(char *line, char **a, char **b, char **c) {
    *a = line;
    char *p1 = strchr(line, ',');
    if (!p1) {
        return -1;
    }
    *p1 = '\0';
    *b = p1 + 1;
    char *p2 = strchr(*b, ',');
    if (!p2) {
        return -1;
    }
    *p2 = '\0';
    *c = p2 + 1;
    return 0;
}

int load_interval_csv(const char *path, IntervalRow *rows, int max_rows, int *out_count) {
    FILE *fp = fopen(path, "r");
    if (!fp) {
        return -1;
    }
    char line[512];
    if (!fgets(line, sizeof(line), fp)) {
        fclose(fp);
        return -1;
    }
    int count = 0;
    while (fgets(line, sizeof(line), fp)) {
        trim_newline(line);
        if (line[0] == '\0') {
            continue;
        }
        if (count >= max_rows) {
            fclose(fp);
            return -1;
        }
        char *f1 = NULL;
        char *f2 = NULL;
        char *f3 = NULL;
        if (split_three(line, &f1, &f2, &f3) != 0) {
            fclose(fp);
            return -1;
        }
        strncpy(rows[count].meter_id, f1, TOU_ID_LEN - 1);
        rows[count].meter_id[TOU_ID_LEN - 1] = '\0';
        strncpy(rows[count].timestamp, f2, TOU_TS_LEN - 1);
        rows[count].timestamp[TOU_TS_LEN - 1] = '\0';
        if (parse_double_field(f3, &rows[count].register_kwh) != 0) {
            fclose(fp);
            return -1;
        }
        count += 1;
    }
    fclose(fp);
    *out_count = count;
    return 0;
}
