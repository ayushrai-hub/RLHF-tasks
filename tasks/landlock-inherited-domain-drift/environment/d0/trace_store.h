#ifndef TRACE_STORE_H
#define TRACE_STORE_H

#define TRACE_MAX_ROWS 16

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
} trace_row_t;

void trace_store_clear(void);
int trace_store_add(const trace_row_t *row);
int trace_store_count(void);
int trace_store_get(int idx, trace_row_t *out);

#endif
