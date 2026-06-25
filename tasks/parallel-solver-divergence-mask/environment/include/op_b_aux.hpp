#pragma once

#include "types.hpp"

bool fold_lane_selected(int lane_token, int cover);
double label_fold_density(const FoldPack* packs, int count);
