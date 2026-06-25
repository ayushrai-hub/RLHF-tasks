#pragma once

#include "types.hpp"

double adjust_dispersion_for_tick(double spread, double scalar, int tick);
int flush_window_from_tick(const TraceRow& row);
