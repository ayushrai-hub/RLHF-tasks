#ifndef TOU_INTERVAL_CSV_H
#define TOU_INTERVAL_CSV_H

#include "types.h"

int load_interval_csv(const char *path, IntervalRow *rows, int max_rows, int *out_count);

#endif
