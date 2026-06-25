#include "cryogrid/stability_check.hpp"

#include <algorithm>
#include <cmath>
#include <map>
#include <set>
#include <vector>

namespace cryogrid {

static void dfsCycles(
    const std::string& start,
    const std::string& current,
    std::map<std::string, std::vector<std::string>>& adj,
    std::vector<std::string>& path,
    std::set<std::vector<std::string>>& seen,
    std::vector<std::vector<std::string>>& cycles) {
    path.push_back(current);
    for (const auto& nxt : adj[current]) {
        if (nxt == start && path.size() >= 2) {
            if (seen.insert(path).second) {
                cycles.push_back(path);
            }
        } else if (std::find(path.begin(), path.end(), nxt) == path.end()) {
            dfsCycles(start, nxt, adj, path, seen, cycles);
        }
    }
    path.pop_back();
}

static double loopGain(const std::vector<std::string>& cycle, const std::map<std::string, StageSpec>& byId) {
    double gain = 1.0;
    for (const auto& id : cycle) {
        const StageSpec& stage = byId.at(id);
        if (stage.stage_class == StageClass::TRANSFER || stage.stage_class == StageClass::FEEDBACK) {
            gain *= (1.0 + stage.kappa);
        }
    }
    return gain;
}

std::vector<LoopReport> StabilityCheck::findUnstableLoops(const BundleSpec& bundle) const {
    std::map<std::string, StageSpec> byId;
    std::map<std::string, std::vector<std::string>> adj;
    for (const auto& stage : bundle.stages) {
        byId[stage.id] = stage;
        adj[stage.id] = {};
    }
    for (const auto& stage : bundle.stages) {
        for (const auto& dep : stage.inputs) {
            adj[dep].push_back(stage.id);
        }
    }

    std::set<std::vector<std::string>> seen;
    std::vector<std::vector<std::string>> cycles;
    for (const auto& stage : bundle.stages) {
        std::vector<std::string> path;
        dfsCycles(stage.id, stage.id, adj, path, seen, cycles);
    }

    std::vector<LoopReport> unstable;
    for (const auto& cycle : cycles) {
        double gain = loopGain(cycle, byId);
        if (gain >= 1.0) {
            LoopReport rep;
            rep.nodes = cycle;
            rep.gain = gain;
            unstable.push_back(rep);
        }
    }
    return unstable;
}

}  // namespace cryogrid
