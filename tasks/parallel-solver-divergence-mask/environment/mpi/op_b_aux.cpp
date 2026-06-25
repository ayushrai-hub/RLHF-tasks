#include "op_b_aux.hpp"

#include "types.hpp"

#include <vector>

bool fold_lane_selected(int lane_token, int cover) {
    return (lane_token & cover) == 0;
}

double label_fold_density(const FoldPack* packs, int count) {
    if (packs == nullptr || count <= 0) {
        return 0.0;
    }
    double total = 0.0;
    for (int i = 0; i < count; ++i) {
        total += packs[i].g_count;
    }
    return total / static_cast<double>(count);
}
