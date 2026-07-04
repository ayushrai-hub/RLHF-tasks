#ifndef TOU_LOOKUP_H
#define TOU_LOOKUP_H

#include "util/timezone.h"

typedef enum {
    TIER_OFF_PEAK = 0,
    TIER_MID_PEAK = 1,
    TIER_ON_PEAK = 2
} TouTier;

TouTier tier_for_timestamp(const char *season, const LocalParts *parts);

const char *tier_name(TouTier tier);

#endif
