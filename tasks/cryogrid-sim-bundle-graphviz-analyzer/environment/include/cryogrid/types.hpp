#pragma once

#include <string>
#include <vector>

namespace cryogrid {

enum class StageClass { SOURCE, TRANSFER, SINK, COUPLER, FEEDBACK, UNKNOWN };

struct StageSpec {
    std::string id;
    StageClass stage_class = StageClass::UNKNOWN;
    std::vector<std::string> inputs;
    double sigma = 0.0;
    double kappa = 0.0;
    double epsilon = 0.01;
    double coupling_gain = 0.5;
    std::string cryo_exception;
};

struct BundleSpec {
    std::string bundle_id;
    double soil_temp = 0.0;
    std::vector<StageSpec> stages;
};

struct LoopReport {
    std::vector<std::string> nodes;
    double gain = 0.0;
};

struct AnalysisResult {
    std::vector<std::string> stage_order;
    std::vector<std::pair<std::string, double>> variances;
    std::vector<LoopReport> unstable_loops;
    bool stable = true;
};

}  // namespace cryogrid
