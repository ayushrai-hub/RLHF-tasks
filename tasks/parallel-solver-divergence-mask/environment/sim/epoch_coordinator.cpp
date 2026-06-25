#include "epoch_coordinator.hpp"

#include <numeric>

namespace {

double spread_delta(double checkpoint_dispersion, double stream_spread) {
    return checkpoint_dispersion - stream_spread;
}

}  // namespace

void apply_continued_weight_adjustment(
    std::vector<double>& weights,
    const std::vector<double>& values,
    double checkpoint_dispersion,
    double stream_spread,
    const std::string& mode,
    int phase_id) {
    if (mode != "continued" || phase_id < 1) {
        return;
    }
    const double delta = spread_delta(checkpoint_dispersion, stream_spread);
    if (std::abs(delta) < 1e-18) {
        return;
    }
    const double total = std::accumulate(values.begin(), values.end(), 0.0);
    if (total <= 0.0) {
        return;
    }
    for (size_t i = 0; i < weights.size(); ++i) {
        weights[i] += (values[i] / total) * delta * 1e-6;
        if (weights[i] < 0.0001) {
            weights[i] = 0.0001;
        }
    }
    const double wsum = std::accumulate(weights.begin(), weights.end(), 0.0);
    for (double& w : weights) {
        w /= wsum;
    }
}
