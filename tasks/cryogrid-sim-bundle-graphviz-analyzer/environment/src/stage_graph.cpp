#include "cryogrid/stage_graph.hpp"

#include <algorithm>

namespace cryogrid {

std::vector<std::string> StageGraph::pipelineOrder(const BundleSpec& bundle) const {
    std::vector<std::string> order;
    for (const auto& stage : bundle.stages) {
        order.push_back(stage.id);
    }
    return order;
}

std::vector<std::string> StageGraph::dependencyOrder(const BundleSpec& bundle) const {
    std::vector<std::string> order;
    for (const auto& stage : bundle.stages) {
        order.push_back(stage.id);
    }
    std::sort(order.begin(), order.end());
    return order;
}

}  // namespace cryogrid
