#include "schedule/tier_context.h"

#include "schedule/season.h"
#include "schedule/tou_lookup.h"
#include "util/timezone.h"

TouTier tou_tier_for_interval(const char *interval_start_ts, const char *interval_end_ts) {
    LocalParts start_parts;
    LocalParts end_parts;
    if (parse_timestamp(interval_start_ts, &start_parts) != 0) {
        return TIER_OFF_PEAK;
    }
    if (parse_timestamp(interval_end_ts, &end_parts) != 0) {
        return TIER_OFF_PEAK;
    }
    const char *season = season_for_parts(&end_parts);
    return tier_for_timestamp(season, &start_parts);
}
