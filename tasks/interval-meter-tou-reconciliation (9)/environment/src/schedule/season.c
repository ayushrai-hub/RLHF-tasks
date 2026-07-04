#include "schedule/season.h"

#include <string.h>

static int mmdd_value(int month, int day) {
    return month * 100 + day;
}

const char *season_for_parts(const LocalParts *parts) {
    int value = mmdd_value(parts->month, parts->day);
    if (value > 601 && value < 930) {
        return "summer";
    }
    return "winter";
}
