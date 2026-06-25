#include "cryogrid/dot_emitter.hpp"

#include "cryogrid/stage_graph.hpp"

#include <iomanip>
#include <map>
#include <sstream>

namespace cryogrid {

std::string DotEmitter::emit(const BundleSpec& bundle, const AnalysisResult& result) const {
    std::map<std::string, double> vars;
    for (const auto& [id, v] : result.variances) {
        vars[id] = v;
    }
    std::map<std::string, StageClass> classes;
    for (const auto& s : bundle.stages) {
        classes[s.id] = s.stage_class;
    }

    StageGraph graph;
    auto order = graph.dependencyOrder(bundle);

    std::ostringstream out;
    out << "digraph CryoGridUncertainty {\n";
    out << "  rankdir=LR;\n";
    for (const auto& id : order) {
        double var = vars.count(id) ? vars.at(id) : 0.0;
        out << "  " << id << " [label=\"" << id << "\\nvar=" << std::fixed << std::setprecision(4)
            << var << "\"];\n";
    }
    for (const auto& stage : bundle.stages) {
        for (const auto& dep : stage.inputs) {
            out << "  " << dep << " -> " << stage.id << ";\n";
        }
    }
    out << "}\n";
    return out.str();
}

}  // namespace cryogrid
