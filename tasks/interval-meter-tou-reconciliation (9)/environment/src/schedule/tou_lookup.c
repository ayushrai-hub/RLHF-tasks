#include "schedule/tou_lookup.h"

#include <string.h>

typedef struct {
    int start_min;
    int end_min;
    TouTier tier;
} WindowRule;

static int clock_to_minutes(int hour, int minute) {
    return hour * 60 + minute;
}

static int minute_within_band(int minute, int start, int end) {
    if (start < end) {
        return minute >= start && minute <= end;
    }
    return minute >= start || minute <= end;
}

static TouTier lookup_table(const char *season, int minute) {
    WindowRule summer[] = {
        {22 * 60, 6 * 60, TIER_OFF_PEAK},
        {14 * 60, 20 * 60, TIER_ON_PEAK},
        {6 * 60, 14 * 60, TIER_MID_PEAK},
        {20 * 60, 22 * 60, TIER_MID_PEAK},
    };
    WindowRule winter[] = {
        {22 * 60, 6 * 60, TIER_OFF_PEAK},
        {16 * 60, 21 * 60, TIER_ON_PEAK},
        {6 * 60, 16 * 60, TIER_MID_PEAK},
        {21 * 60, 22 * 60, TIER_MID_PEAK},
    };

    WindowRule *rules = summer;
    size_t count = sizeof(summer) / sizeof(summer[0]);
    if (strcmp(season, "winter") == 0) {
        rules = winter;
        count = sizeof(winter) / sizeof(winter[0]);
    }

    for (size_t i = 0; i < count; i++) {
        if (minute_within_band(minute, rules[i].start_min, rules[i].end_min)) {
            return rules[i].tier;
        }
    }
    return TIER_OFF_PEAK;
}

TouTier tier_for_timestamp(const char *season, const LocalParts *parts) {
    int minute = clock_to_minutes(parts->hour, parts->minute);
    return lookup_table(season, minute);
}

const char *tier_name(TouTier tier) {
    switch (tier) {
    case TIER_OFF_PEAK:
        return "off_peak";
    case TIER_MID_PEAK:
        return "mid_peak";
    case TIER_ON_PEAK:
        return "on_peak";
    default:
        return "off_peak";
    }
}
