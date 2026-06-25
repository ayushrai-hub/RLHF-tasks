#include "cap_journal.h"

#include <stdio.h>
#include <string.h>

static const char *journal_path(void)
{
    return "/app/work/cap_journal.tsv";
}

int cap_journal_append(const cap_row_t *row)
{
    if (row == NULL) {
        return -1;
    }
    FILE *fp = fopen(journal_path(), "a");
    if (fp == NULL) {
        return -1;
    }
    (void)fprintf(fp, "%u\t%s\t%s\t%s\t%d\t%s\t%s\t%s\t%s\t%u\n", row->stamp_code, row->round, row->actor, row->mark,
                  row->class_tag, row->cap_effective, row->cap_bound, row->gap_code, row->launch_mark,
                  row->seq_code);
    fclose(fp);
    return 0;
}

int cap_journal_tail_seq(const char *round, const char *actor, const char *mark, unsigned *out_seq)
{
    if (round == NULL || actor == NULL || mark == NULL || out_seq == NULL) {
        return -1;
    }
    FILE *fp = fopen(journal_path(), "r");
    if (fp == NULL) {
        *out_seq = 0;
        return 0;
    }
    unsigned best = 0;
    char line[512];
    while (fgets(line, sizeof(line), fp) != NULL) {
        unsigned seq = 0;
        char r[8];
        char a[16];
        char m[32];
        if (sscanf(line, "%u\t%7s\t%15s\t%31s", &seq, r, a, m) < 4) {
            continue;
        }
        if (strcmp(r, round) == 0 && strcmp(a, actor) == 0 && strcmp(m, mark) == 0 && seq >= best) {
            best = seq;
        }
    }
    fclose(fp);
    *out_seq = best;
    return 0;
}
