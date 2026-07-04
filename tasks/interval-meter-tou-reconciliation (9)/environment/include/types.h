#ifndef TOU_TYPES_H
#define TOU_TYPES_H

#include <stddef.h>
#include <stdint.h>

#define TOU_MAX_METERS 8
#define TOU_MAX_ROWS 4096
#define TOU_MAX_FIXTURES 16
#define TOU_ID_LEN 32
#define TOU_TS_LEN 40

typedef struct {
    char meter_id[TOU_ID_LEN];
    char timestamp[TOU_TS_LEN];
    double register_kwh;
} IntervalRow;

typedef struct {
    char timezone[64];
    double register_max_kwh;
    int interval_minutes;
    int demand_window_intervals;
} TariffConfig;

typedef struct {
    int interval_count;
    double total_kwh;
    double tier_off_peak;
    double tier_mid_peak;
    double tier_on_peak;
    double demand_peak_kw;
    int rollover_events;
    int gap_intervals;
    int reconciled;
    double register_delta_kwh;
} MeterStats;

typedef struct {
    char name[TOU_ID_LEN];
    char csv_path[256];
} FixtureSet;

typedef struct {
    TariffConfig tariff;
    FixtureSet fixtures[TOU_MAX_FIXTURES];
    int fixture_count;
} RunConfig;

#endif
