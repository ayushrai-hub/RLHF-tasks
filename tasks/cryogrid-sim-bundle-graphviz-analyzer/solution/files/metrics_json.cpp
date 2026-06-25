#include "cryogrid/metrics_json.hpp"

#include <iomanip>
#include <sstream>

namespace cryogrid {

std::string MetricsJson::emit(const BundleSpec& bundle, const AnalysisResult& result) const {
    std::ostringstream out;
    out << std::fixed << std::setprecision(6);
    out << "{\n";
    out << "  \"bundle_id\": \"" << bundle.bundle_id << "\",\n";
    out << "  \"stable\": " << (result.stable ? "true" : "false") << ",\n";
    out << "  \"stage_order\": [";
    for (size_t i = 0; i < result.stage_order.size(); ++i) {
        if (i) out << ", ";
        out << "\"" << result.stage_order[i] << "\"";
    }
    out << "],\n";
    out << "  \"stage_variances\": {\n";
    for (size_t i = 0; i < result.variances.size(); ++i) {
        const auto& [id, val] = result.variances[i];
        out << "    \"" << id << "\": " << val;
        if (i + 1 < result.variances.size()) {
            out << ",";
        }
        out << "\n";
    }
    out << "  },\n";
    out << "  \"unstable_loops\": [";
    for (size_t i = 0; i < result.unstable_loops.size(); ++i) {
        if (i) out << ", ";
        const auto& loop = result.unstable_loops[i];
        out << "\n    {\"nodes\": [";
        for (size_t j = 0; j < loop.nodes.size(); ++j) {
            if (j) out << ", ";
            out << "\"" << loop.nodes[j] << "\"";
        }
        out << "], \"gain\": " << loop.gain << "}";
    }
    if (!result.unstable_loops.empty()) {
        out << "\n  ";
    }
    out << "]\n";
    out << "}\n";
    return out.str();
}

}  // namespace cryogrid
