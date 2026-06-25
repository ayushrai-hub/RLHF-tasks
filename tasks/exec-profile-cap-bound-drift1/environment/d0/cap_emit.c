#include "cap_layout.h"
#include "cap_store.h"
#include "sha256.h"

#include <stdio.h>
#include <string.h>

static void row_effective_hash(const cap_row_t *row, char out[65])
{
    char payload[512];
    (void)snprintf(payload, sizeof(payload),
                   "{\"actor\":\"%s\",\"cap_bound\":\"%s\",\"cap_effective\":\"%s\",\"class_tag\":%d,"
                   "\"mark\":\"%s\",\"round\":\"%s\"}",
                   row->actor, row->cap_bound, row->cap_effective, row->class_tag, row->mark, row->round);
    cap_sha256_hex((const uint8_t *)payload, strlen(payload), out);
}

static void row_bound_hash(const cap_row_t *row, char out[65])
{
    cap_sha256_hex((const uint8_t *)row->cap_bound, strlen(row->cap_bound), out);
}

int emit_cap_json(const char *out_path)
{
    FILE *out = fopen(out_path, "w");
    if (out == NULL) {
        return -1;
    }
    cap_row_t rows[CAP_MAX_ROWS];
    int n = cap_store_count();
    for (int i = 0; i < n; i++) {
        if (cap_store_get(i, &rows[i]) != 0) {
            return -1;
        }
        row_effective_hash(&rows[i], rows[i].effective_set_hash);
        row_bound_hash(&rows[i], rows[i].bound_set_hash);
    }
    (void)fprintf(out, "{\n  \"rows\": [\n");
    int first = 1;
    for (int i = 0; i < n; i++) {
        cap_row_t *row = &rows[i];
        if (!first) {
            (void)fprintf(out, ",\n");
        }
        first = 0;
        (void)fprintf(out,
                      "    {\"round\": \"%s\", \"actor\": \"%s\", \"mark\": \"%s\", \"class_tag\": %d, "
                      "\"effective_set_hash\": \"%s\", \"bound_set_hash\": \"%s\", \"gap_code\": \"%s\", "
                      "\"launch_mark\": \"%s\", \"stamp_code\": %u, \"seq_code\": %u}",
                      row->round, row->actor, row->mark, row->class_tag, row->effective_set_hash, row->bound_set_hash,
                      row->gap_code, row->launch_mark, row->stamp_code, row->seq_code);
    }
    (void)fprintf(out, "\n  ]\n}\n");
    fclose(out);
    return 0;
}
