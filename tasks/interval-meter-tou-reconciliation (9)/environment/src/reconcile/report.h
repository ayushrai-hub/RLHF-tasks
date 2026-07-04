#ifndef TOU_REPORT_H
#define TOU_REPORT_H

#include "types.h"

typedef struct {
    char meter_id[TOU_ID_LEN];
    MeterStats stats;
} MeterReport;

typedef struct {
    char name[TOU_ID_LEN];
    MeterReport meters[TOU_MAX_METERS];
    int meter_count;
} FixtureReport;

typedef struct {
    char timezone[64];
    FixtureReport fixtures[TOU_MAX_FIXTURES];
    int fixture_count;
    int all_reconciled;
} ReconciliationReport;

int write_report_json(const ReconciliationReport *report, const char *out_path);

#endif
