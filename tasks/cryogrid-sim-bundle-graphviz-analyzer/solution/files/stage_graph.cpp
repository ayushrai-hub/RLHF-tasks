#include "cryogrid/stage_graph.hpp"

#include <algorithm>
#include <map>
#include <queue>
#include <set>

namespace cryogrid {

std::vector<std::string> StageGraph::pipelineOrder(const BundleSpec& bundle) const {
    std::vector<std::string> order;
    for (const auto& stage : bundle.stages) {
        order.push_back(stage.id);
    }
    return order;
}

std::vector<std::string> StageGraph::dependencyOrder(const BundleSpec& bundle) const {
    std::map<std::string, int> indegree;
    std::map<std::string, std::vector<std::string>> adj;
    for (const auto& stage : bundle.stages) {
        indegree.emplace(stage.id, 0);
    }
    for (const auto& stage : bundle.stages) {
        for (const auto& dep : stage.inputs) {
            adj[dep].push_back(stage.id);
            indegree[stage.id]++;
        }
    }
    std::queue<std::string> q;
    for (const auto& [id, deg] : indegree) {
        if (deg == 0) {
            q.push(id);
        }
    }
    std::vector<std::string> order;
    while (!q.empty()) {
        std::string cur = q.front();
        q.pop();
        order.push_back(cur);
        for (const auto& nxt : adj[cur]) {
            if (--indegree[nxt] == 0) {
                q.push(nxt);
            }
        }
    }
    if (order.size() != bundle.stages.size()) {
        for (const auto& stage : bundle.stages) {
            if (std::find(order.begin(), order.end(), stage.id) == order.end()) {
                order.push_back(stage.id);
            }
        }
    }
    return order;
}

}  // namespace cryogrid
