#include "cap_store.h"
#include "cap_journal.h"

#include <stdio.h>
#include <string.h>

static cap_row_t g_rows[CAP_MAX_ROWS];
static int g_count = 0;

static const char *store_path(void)
{
    return "/app/work/cap_store.tsv";
}

int cap_store_clear(void)
{
    g_count = 0;
    return cap_store_save();
}

int cap_store_load(void)
{
    FILE *fp = fopen(store_path(), "r");
    g_count = 0;
    if (fp == NULL) {
        return 0;
    }
    char line[512];
    while (fgets(line, sizeof(line), fp) != NULL && g_count < CAP_MAX_ROWS) {
        cap_row_t row;
        memset(&row, 0, sizeof(row));
        if (sscanf(line, "%7s\t%15s\t%31s\t%d\t%15s\t%15s\t%7s\t%31s\t%u\t%u", row.round, row.actor,
                   row.mark, &row.class_tag, row.cap_effective, row.cap_bound, row.gap_code, row.launch_mark,
                   &row.stamp_code, &row.seq_code) < 10) {
            continue;
        }
        g_rows[g_count++] = row;
    }
    fclose(fp);
    return 0;
}

int cap_store_save(void)
{
    FILE *fp = fopen(store_path(), "w");
    if (fp == NULL) {
        return -1;
    }
    for (int i = 0; i < g_count; i++) {
        cap_row_t *row = &g_rows[i];
        (void)fprintf(fp, "%s\t%s\t%s\t%d\t%s\t%s\t%s\t%s\t%u\t%u\n", row->round, row->actor, row->mark,
                      row->class_tag, row->cap_effective, row->cap_bound, row->gap_code, row->launch_mark,
                      row->stamp_code, row->seq_code);
    }
    fclose(fp);
    return 0;
}

int cap_store_count(void)
{
    return g_count;
}

int cap_store_get(int index, cap_row_t *row)
{
    if (row == NULL || index < 0 || index >= g_count) {
        return -1;
    }
    *row = g_rows[index];
    return 0;
}

int cap_store_find(const char *round, const char *actor, const char *mark, cap_row_t *row)
{
    for (int i = 0; i < g_count; i++) {
        if (strcmp(g_rows[i].round, round) == 0 && strcmp(g_rows[i].actor, actor) == 0 &&
            strcmp(g_rows[i].mark, mark) == 0) {
            if (row != NULL) {
                *row = g_rows[i];
            }
            return 0;
        }
    }
    return -1;
}

static unsigned next_seq(const cap_row_t *row)
{
    unsigned tail = 0;
    (void)cap_journal_tail_seq(row->round, row->actor, row->mark, &tail);
    return tail + 1;
}

int cap_store_upsert(const cap_row_t *row)
{
    if (row == NULL) {
        return -1;
    }
    cap_row_t copy = *row;
    if (copy.seq_code == 0) {
        copy.seq_code = next_seq(&copy);
    }
    for (int i = 0; i < g_count; i++) {
        if (strcmp(g_rows[i].round, copy.round) == 0 && strcmp(g_rows[i].actor, copy.actor) == 0 &&
            strcmp(g_rows[i].mark, copy.mark) == 0) {
            g_rows[i] = copy;
            (void)cap_journal_append(&copy);
            return cap_store_save();
        }
    }
    if (g_count >= CAP_MAX_ROWS) {
        return -1;
    }
    g_rows[g_count++] = copy;
    (void)cap_journal_append(&copy);
    return cap_store_save();
}
