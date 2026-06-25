#pragma once

#include "types.hpp"

#include <vector>

double mix_value(int seed, int index);
double stream_mean(const std::vector<double>& values);
double stream_spread(const std::vector<double>& values);

struct StreamFoldStats {
    double mean;
    double spread;
};

StreamFoldStats stream_fold_stats(int seed, const std::vector<CaseRow>& rows);
void build_case_values(int seed, const std::vector<CaseRow>& rows, std::vector<double>& values);