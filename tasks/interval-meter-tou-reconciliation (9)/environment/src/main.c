#include "aggregate/meter_roll.h"
#include "parse/config_load.h"
#include "parse/interval_csv.h"
#include "reconcile/report.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int compare_rows(const void *a, const void *b) {
    const IntervalRow *ra = (const IntervalRow *)a;
    const IntervalRow *rb = (const IntervalRow *)b;
    int cmp = strcmp(ra->meter_id, rb->meter_id);
    if (cmp != 0) {
        return cmp;
    }
    return strcmp(ra->timestamp, rb->timestamp);
}

static int unique_meter_count(IntervalRow *rows, int count) {
    int meters = 0;
    for (int i = 0; i < count; i++) {
        if (i == 0 || strcmp(rows[i].meter_id, rows[i - 1].meter_id) != 0) {
            meters += 1;
        }
    }
    return meters;
}

static void fill_fixture_report(const RunConfig *cfg, const FixtureSet *fx, FixtureReport *out) {
    IntervalRow rows[TOU_MAX_ROWS];
    int row_count = 0;
    strncpy(out->name, fx->name, TOU_ID_LEN - 1);
    out->meter_count = 0;
    if (load_interval_csv(fx->csv_path, rows, TOU_MAX_ROWS, &row_count) != 0) {
        return;
    }
    qsort(rows, (size_t)row_count, sizeof(IntervalRow), compare_rows);

    int idx = 0;
    while (idx < row_count && out->meter_count < TOU_MAX_METERS) {
        IntervalRow slice[TOU_MAX_ROWS];
        int slice_count = 0;
        strncpy(slice[0].meter_id, rows[idx].meter_id, TOU_ID_LEN - 1);
        while (idx < row_count && strcmp(rows[idx].meter_id, slice[0].meter_id) == 0) {
            slice[slice_count++] = rows[idx++];
        }
        MeterStats stats;
        aggregate_meter(slice, slice_count, &cfg->tariff, &stats);
        strncpy(out->meters[out->meter_count].meter_id, slice[0].meter_id, TOU_ID_LEN - 1);
        out->meters[out->meter_count].stats = stats;
        out->meter_count += 1;
    }
}

int main(int argc, char **argv) {
    const char *config_path = "/app/environment/config/run.json";
    const char *out_path = "/app/output/reconciliation_report.json";
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--config") == 0 && i + 1 < argc) {
            config_path = argv[++i];
        } else if (strcmp(argv[i], "--out") == 0 && i + 1 < argc) {
            out_path = argv[++i];
        }
    }

    RunConfig cfg;
    if (load_run_config(config_path, &cfg) != 0) {
        fprintf(stderr, "failed to load config\n");
        return 1;
    }

    ReconciliationReport report;
    memset(&report, 0, sizeof(report));
    strncpy(report.timezone, cfg.tariff.timezone, sizeof(report.timezone) - 1);
    report.fixture_count = cfg.fixture_count;
    report.all_reconciled = 1;

    for (int i = 0; i < cfg.fixture_count; i++) {
        fill_fixture_report(&cfg, &cfg.fixtures[i], &report.fixtures[i]);
        for (int j = 0; j < report.fixtures[i].meter_count; j++) {
            if (!report.fixtures[i].meters[j].stats.reconciled) {
                report.all_reconciled = 0;
            }
        }
    }

    if (write_report_json(&report, out_path) != 0) {
        fprintf(stderr, "failed to write report\n");
        return 1;
    }
    return 0;
}
