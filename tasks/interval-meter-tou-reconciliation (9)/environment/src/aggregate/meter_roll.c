#include "aggregate/meter_roll.h"

#include "aggregate/demand_track.h"
#include "aggregate/gap_elapsed.h"
#include "aggregate/interval_energy.h"
#include "schedule/tier_context.h"
#include "util/timezone.h"

#include <math.h>
#include <string.h>

static int same_meter(const char *a, const char *b) {
    return strcmp(a, b) == 0;
}

void aggregate_meter(const IntervalRow *rows, int row_count, const TariffConfig *tariff, MeterStats *stats) {
    memset(stats, 0, sizeof(*stats));
    if (row_count <= 0) {
        return;
    }

    DemandTrack demand;
    demand_track_reset(&demand);

    for (int i = 0; i < row_count; i++) {
        if (i > 0 && !same_meter(rows[i].meter_id, rows[i - 1].meter_id)) {
            continue;
        }
        if (i == 0) {
            continue;
        }

        int rollover = 0;
        double delta = interval_kwh_delta(
            rows[i - 1].register_kwh,
            rows[i].register_kwh,
            tariff->register_max_kwh,
            &rollover
        );
        stats->rollover_events += rollover;

        stats->gap_intervals += gap_slots_between(
            rows[i - 1].timestamp,
            rows[i].timestamp,
            tariff->demand_window_intervals
        );

        stats->interval_count += 1;
        stats->total_kwh += delta;
        stats->register_delta_kwh += rows[i].register_kwh - rows[i - 1].register_kwh;

        TouTier tier = tou_tier_for_interval(rows[i - 1].timestamp, rows[i].timestamp);
        if (tier == TIER_OFF_PEAK) {
            stats->tier_off_peak += delta;
        } else if (tier == TIER_MID_PEAK) {
            stats->tier_mid_peak += delta;
        } else {
            stats->tier_on_peak += delta;
        }

        double demand_kw = delta * 60.0 / (double)tariff->interval_minutes;
        demand_track_note(&demand, demand_kw);
    }

    stats->demand_peak_kw = demand_track_finalize(&demand);
    stats->reconciled = fabs(stats->total_kwh - stats->register_delta_kwh) < 0.001 ? 1 : 0;
}
