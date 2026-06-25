#include <stdio.h>

static const char *LEDGER_PATH = "/app/work/round.seq";

int seq_advance(int *out_seq)
{
    if (out_seq == NULL) {
        return -1;
    }
    int cur = 0;
    FILE *f = fopen(LEDGER_PATH, "r");
    if (f != NULL) {
        if (fscanf(f, "%d", &cur) != 1) {
            cur = 0;
        }
        fclose(f);
    }
    *out_seq = cur + 1;
    f = fopen(LEDGER_PATH, "w");
    if (f == NULL) {
        return -1;
    }
    (void)fprintf(f, "%d\n", cur + 1);
    fclose(f);
    return 0;
}
