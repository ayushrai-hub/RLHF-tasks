#ifndef TOU_METER_ROLL_H
#define TOU_METER_ROLL_H

#include "types.h"

void aggregate_meter(const IntervalRow *rows, int row_count, const TariffConfig *tariff, MeterStats *stats);

#endif
