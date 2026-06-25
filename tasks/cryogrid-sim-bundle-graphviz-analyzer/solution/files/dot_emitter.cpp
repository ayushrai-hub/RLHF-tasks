#include "cryogrid/dot_emitter.hpp"

#include "cryogrid/stage_graph.hpp"

#include <iomanip>
#include <map>
#include <sstream>

namespace cryogrid {

static std::string classLabel(StageClass cls) {
    switch (cls) {
        case StageClass::SOURCE:
            return "SOURCE";
        case StageClass::TRANSFER:
            return "TRANSFER";
        case StageClass::SINK:
            return "SINK";
        case StageClass::COUPLER:
            return "COUPLER";
        case StageClass::FEEDBACK:
            return "FEEDBACK";
        default:
            return "UNKNOWN";
    }
}

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
    auto order = graph.pipelineOrder(bundle);

    std::ostringstream out;
    out << "digraph CryoGridUncertainty {\n";
    out << "  rankdir=LR;\n";
    for (const auto& id : order) {
        double var = vars.count(id) ? vars.at(id) : 0.0;
        out << "  " << id << " [label=\"" << id << "\\nvar=" << std::fixed << std::setprecision(6)
            << var << "\\nclass=" << classLabel(classes.at(id)) << "\"];\n";
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
