#include "cryogrid/stage_graph.hpp"
#include "cryogrid/variance_engine.hpp"

#include <cmath>

namespace cryogrid {

static double inputVariance(const std::map<std::string, double>& vars, const StageSpec& stage) {
    if (stage.inputs.empty()) {
        return 0.0;
    }
    if (stage.inputs.size() == 1) {
        auto it = vars.find(stage.inputs.front());
        return it == vars.end() ? 0.0 : it->second;
    }
    double sum = 0.0;
    for (const auto& id : stage.inputs) {
        auto it = vars.find(id);
        if (it != vars.end()) {
            sum += it->second;
        }
    }
    return sum;
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
        double varIn = inputVariance(vars, stage);
        double varOut = 0.0;
        switch (stage.stage_class) {
            case StageClass::SOURCE:
                varOut = stage.sigma * stage.sigma;
                break;
            case StageClass::TRANSFER:
            case StageClass::FEEDBACK:
                varOut = varIn + stage.kappa + stage.epsilon;
                break;
            case StageClass::SINK:
                varOut = varIn;
                break;
            case StageClass::COUPLER:
                varOut = varIn * stage.coupling_gain;
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
