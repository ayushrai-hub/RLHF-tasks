#include "cryogrid/stage_graph.hpp"
#include "cryogrid/variance_engine.hpp"

#include <cmath>

namespace cryogrid {

static double sumInputVariance(const std::map<std::string, double>& vars, const StageSpec& stage) {
    double sum = 0.0;
    for (const auto& id : stage.inputs) {
        auto it = vars.find(id);
        if (it != vars.end()) {
            sum += it->second;
        }
    }
    return sum;
}

static double effectiveEpsilon(const BundleSpec& bundle, const StageSpec& stage) {
    double eps = stage.epsilon;
    if (stage.cryo_exception == "frozen_soil" && bundle.soil_temp < -0.5) {
        eps = std::max(eps, 0.02);
    }
    return eps;
}

std::map<std::string, double> VarianceEngine::compute(const BundleSpec& bundle) const {
    StageGraph graph;
    auto order = graph.dependencyOrder(bundle);
    std::map<std::string, StageSpec> byId;
    for (const auto& s : bundle.stages) {
        byId[s.id] = s;
    }

    std::map<std::string, double> vars;
    for (const auto& id : order) {
        const StageSpec& stage = byId.at(id);
        double varIn = sumInputVariance(vars, stage);
        double varOut = 0.0;
        switch (stage.stage_class) {
            case StageClass::SOURCE:
                varOut = stage.sigma * stage.sigma;
                break;
            case StageClass::TRANSFER:
            case StageClass::FEEDBACK: {
                double eps = effectiveEpsilon(bundle, stage);
                double base = stage.inputs.size() == 1 ? varIn : varIn;
                varOut = base * std::pow(1.0 + stage.kappa, 2.0) + eps * eps;
                break;
            }
            case StageClass::SINK:
                varOut = varIn;
                break;
            case StageClass::COUPLER:
                varOut = varIn * stage.coupling_gain + stage.sigma * stage.sigma;
                break;
            default:
                varOut = 0.0;
                break;
        }
        vars[id] = varOut;
    }
    return vars;
}

}  // namespace cryogrid
