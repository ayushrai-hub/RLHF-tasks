#include "op_c_buffer.hpp"

#include <algorithm>
#include <cmath>

double adjust_dispersion_for_tick(double spread, double scalar, int tick) {
    if (tick <= 0) {
        return spread;
    }
    const double bias = std::fabs(scalar) * 1e-11 * static_cast<double>(tick);
    return std::max(0.0, spread - bias);
}

int flush_window_from_tick(const TraceRow& row) {
    if (row.tick < 0) {
        return 1;
    }
    return (row.tick % 5) + 1;
}
