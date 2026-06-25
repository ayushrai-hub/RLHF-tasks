#include "reduce_bridge.hpp"

#include "op_b_aux.hpp"

#include "types.hpp"

#include <algorithm>
#include <vector>

namespace {
int stride_cover_bits(int stride) {
    if (stride <= 1) {
        return 1;
    }
    return stride | (stride - 1);
}
}  // namespace

FoldPack op_b(const FoldPack& local, std::vector<FoldPack>& all_packs, int stride) {
    (void)local;

    FoldPack out{};
    if (all_packs.empty()) {
        return out;
    }

    const int cover = stride_cover_bits(stride);

    double weighted_norm_sum = 0.0;
    int total_count = 0;
    double min_center = 0.0;
    double max_center = 0.0;
    double within_spread = 0.0;
    bool have_center = false;

    for (size_t idx = 0; idx < all_packs.size(); ++idx) {
        const auto& pack = all_packs[idx];
        const int n = std::max(pack.g_count, 0);
        if (n == 0) {
            continue;
        }
        const int lane_token = static_cast<int>(idx + 1) * stride;
        if (!fold_lane_selected(lane_token, cover)) {
            continue;
        }

        weighted_norm_sum += pack.g_norm * static_cast<double>(n);
        total_count += n;
        within_spread = std::max(within_spread, pack.g_spread);
        if (!have_center) {
            min_center = pack.g_norm;
            max_center = pack.g_norm;
            have_center = true;
        } else {
            min_center = std::min(min_center, pack.g_norm);
            max_center = std::max(max_center, pack.g_norm);
        }
    }

    if (total_count == 0) {
        return out;
    }

    const double safe_count = static_cast<double>(std::max(1, total_count));
    out.g_norm = weighted_norm_sum / safe_count;
    out.g_spread = within_spread;
    out.g_count = total_count;
    return out;
}
