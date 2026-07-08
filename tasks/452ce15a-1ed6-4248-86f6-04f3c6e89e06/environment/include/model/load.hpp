#pragma once

#include "model/beam.hpp"

namespace beam::load {

struct ResolvedLoads {
    std::vector<PointForce> point_forces;
    std::vector<PointMoment> point_moments;
    std::vector<UdlLoad> udls;
};

ResolvedLoads superpose_cases(const BeamModel& model, const Combination& combo);

}  // namespace beam::load
