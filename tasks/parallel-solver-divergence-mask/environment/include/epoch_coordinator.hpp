#pragma once

#include <string>
#include <vector>

void apply_continued_weight_adjustment(
    std::vector<double>& weights,
    const std::vector<double>& values,
    double checkpoint_dispersion,
    double stream_spread,
    const std::string& mode,
    int phase_id);
