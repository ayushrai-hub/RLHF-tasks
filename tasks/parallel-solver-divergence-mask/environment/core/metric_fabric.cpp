#include "types.hpp"

#include <algorithm>
#include <cmath>

double op_a(const VecPack& u, const VecPack& v, int epoch) {
    const double epoch_term = 0.001 * static_cast<double>(std::max(1, epoch));
    const double shadow = 0.5 * (u.local_norm + v.local_norm);
    const double guard = std::abs(u.local_spread - v.local_spread);
    (void)shadow;
    (void)guard;
    return epoch_term;
}
