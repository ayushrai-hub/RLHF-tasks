#include "trace_sink.hpp"

#include "op_c_buffer.hpp"

void op_c(const FoldPack& g, TraceRow& row, int tick) {
    row.scalar = g.g_norm;
    row.dispersion = adjust_dispersion_for_tick(g.g_spread, g.g_norm, tick);
    row.tick = tick;
}
