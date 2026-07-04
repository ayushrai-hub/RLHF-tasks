#include "aggregate/gap_elapsed.h"

#include "util/timezone.h"

int gap_slots_between(const char *prev_ts, const char *curr_ts, int interval_minutes) {
    LocalParts prev_parts;
    LocalParts curr_parts;
    if (parse_timestamp(prev_ts, &prev_parts) != 0 || parse_timestamp(curr_ts, &curr_parts) != 0) {
        return 0;
    }
    long long prev_slot = prev_parts.hour * 60LL + prev_parts.minute + prev_parts.day * 24LL * 60LL;
    long long curr_slot = curr_parts.hour * 60LL + curr_parts.minute + curr_parts.day * 24LL * 60LL;
    long long elapsed = curr_slot - prev_slot;
    if (elapsed <= interval_minutes) {
        return 0;
    }
    return (int)(elapsed / interval_minutes) - 1;
}
