#include "../d0/trace_store.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    char profile[32];
    char principal[16];
    char fixture_tag[32];
    char stage_digest_hex[65];
    char reach_digest[17];
    char self_check_field[17];
    char admit_code[8];
    char snap_a_mark[9];
    char snap_b_mark[9];
    char handoff_label[16];
    int layer_pick;
    int rule_count;
    int chain_seq;
} trace_row_blob_t;

static const char *EMIT_PROFILES[] = {"w0_short", "w0_short", "w0_long", "w0_long"};
static const char *EMIT_PRINCIPALS[] = {"direct", "svc", "direct", "svc"};

static int find_row(const trace_row_blob_t *rows, size_t count, const char *profile, const char *principal,
                    trace_row_blob_t *out)
{
    for (size_t i = 0; i < count; i++) {
        if (strcmp(rows[i].profile, profile) == 0 && strcmp(rows[i].principal, principal) == 0) {
            *out = rows[i];
            return 0;
        }
    }
    return -1;
}

int pack_h7(const char *out_path, const void *rows, size_t row_count, size_t row_stride)
{
    if (out_path == NULL || rows == NULL || row_stride < sizeof(trace_row_blob_t)) {
        return -1;
    }
    trace_row_blob_t pool[TRACE_MAX_ROWS];
    for (size_t i = 0; i < row_count; i++) {
        pool[i] = *(const trace_row_blob_t *)((const char *)rows + i * row_stride);
    }
    FILE *out = fopen(out_path, "w");
    if (out == NULL) {
        return -1;
    }
    (void)fprintf(out, "{\n  \"rows\": [\n");
    for (size_t slot = 0; slot < 4; slot++) {
        trace_row_blob_t row;
        if (find_row(pool, row_count, EMIT_PROFILES[slot], EMIT_PRINCIPALS[slot], &row) != 0) {
            fclose(out);
            return -1;
        }
        if (slot > 0) {
            (void)fprintf(out, ",\n");
        }
        (void)fprintf(
            out,
            "    {\"profile\": \"%s\", \"principal\": \"%s\", \"fixture_tag\": \"%s\", "
            "\"stage_digest_hex\": \"%s\", \"reach_digest\": \"%s\", \"self_check_field\": \"%s\", "
            "\"admit_code\": \"%s\", \"snap_a_mark\": \"%s\", \"snap_b_mark\": \"%s\", "
            "\"handoff_label\": \"%s\", \"layer_pick\": %d, \"rule_count\": %d, \"chain_seq\": %d}",
            row.profile, row.principal, row.fixture_tag, row.stage_digest_hex, row.reach_digest,
            row.self_check_field, row.admit_code, row.snap_a_mark, row.snap_b_mark, row.handoff_label,
            row.layer_pick, row.rule_count, row.chain_seq);
    }
    (void)fprintf(out, "\n  ],\n  \"summary\": {\"row_count\": 4, \"trace_stamp\": \"h7-v1\"}\n}\n");
    fclose(out);
    return 0;
}

int emit_trace_json(const char *out_path)
{
    trace_row_t rows[TRACE_MAX_ROWS];
    int n = trace_store_count();
    for (int i = 0; i < n; i++) {
        if (trace_store_get(i, &rows[i]) != 0) {
            return -1;
        }
    }
    return pack_h7(out_path, rows, (size_t)n, sizeof(trace_row_t));
}
