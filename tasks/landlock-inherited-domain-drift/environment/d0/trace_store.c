#include "trace_store.h"

#include <stdio.h>
#include <string.h>

static const char *STORE_PATH = "/app/work/trace_rows.tsv";

static int row_key_match(const trace_row_t *a, const trace_row_t *b)
{
    return strcmp(a->profile, b->profile) == 0 && strcmp(a->principal, b->principal) == 0;
}

void trace_store_clear(void)
{
    FILE *f = fopen(STORE_PATH, "w");
    if (f != NULL) {
        fclose(f);
    }
}

int trace_store_add(const trace_row_t *row)
{
    if (row == NULL) {
        return -1;
    }
    trace_row_t kept[TRACE_MAX_ROWS];
    int kept_n = 0;
    int n = trace_store_count();
    for (int i = 0; i < n; i++) {
        trace_row_t cur;
        if (trace_store_get(i, &cur) != 0) {
            return -1;
        }
        if (!row_key_match(&cur, row)) {
            kept[kept_n++] = cur;
        }
    }
    FILE *f = fopen(STORE_PATH, "w");
    if (f == NULL) {
        return -1;
    }
    for (int i = 0; i < kept_n; i++) {
        (void)fprintf(
            f,
            "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%d\t%d\t%d\n",
            kept[i].profile, kept[i].principal, kept[i].fixture_tag, kept[i].stage_digest_hex,
            kept[i].reach_digest, kept[i].self_check_field, kept[i].admit_code, kept[i].snap_a_mark,
            kept[i].snap_b_mark, kept[i].handoff_label, kept[i].layer_pick, kept[i].rule_count,
            kept[i].chain_seq);
    }
    (void)fprintf(
        f,
        "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%d\t%d\t%d\n",
        row->profile, row->principal, row->fixture_tag, row->stage_digest_hex, row->reach_digest,
        row->self_check_field, row->admit_code, row->snap_a_mark, row->snap_b_mark, row->handoff_label,
        row->layer_pick, row->rule_count, row->chain_seq);
    fclose(f);
    return 0;
}

int trace_store_count(void)
{
    FILE *f = fopen(STORE_PATH, "r");
    if (f == NULL) {
        return 0;
    }
    int count = 0;
    char line[2048];
    while (fgets(line, sizeof(line), f) != NULL) {
        count++;
    }
    fclose(f);
    return count;
}

int trace_store_get(int idx, trace_row_t *out)
{
    if (out == NULL || idx < 0) {
        return -1;
    }
    FILE *f = fopen(STORE_PATH, "r");
    if (f == NULL) {
        return -1;
    }
    char line[2048];
    int cur = 0;
    while (fgets(line, sizeof(line), f) != NULL) {
        if (cur == idx) {
            int pick = 0;
            int rules = 0;
            int chain = 0;
            if (sscanf(line,
                       "%31[^\t]\t%15[^\t]\t%31[^\t]\t%64[^\t]\t%16[^\t]\t%16[^\t]\t%7[^\t]\t%8[^\t]\t%8[^\t]\t%15[^\t]\t%d\t%d\t%d",
                       out->profile, out->principal, out->fixture_tag, out->stage_digest_hex,
                       out->reach_digest, out->self_check_field, out->admit_code, out->snap_a_mark,
                       out->snap_b_mark, out->handoff_label, &pick, &rules, &chain) == 13) {
                out->layer_pick = pick;
                out->rule_count = rules;
                out->chain_seq = chain;
                fclose(f);
                return 0;
            }
            fclose(f);
            return -1;
        }
        cur++;
    }
    fclose(f);
    return -1;
}
