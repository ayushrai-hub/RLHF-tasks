#ifndef TOU_TIER_CONTEXT_H
#define TOU_TIER_CONTEXT_H

#include "schedule/tou_lookup.h"

TouTier tou_tier_for_interval(const char *interval_start_ts, const char *interval_end_ts);

#endif
