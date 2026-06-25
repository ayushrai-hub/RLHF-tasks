#include "cryogrid/metrics_json.hpp"

#include <iomanip>
#include <map>
#include <sstream>

namespace cryogrid {

static std::string stageClassName(StageClass cls) {
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

std::string MetricsJson::emit(const BundleSpec& bundle, const AnalysisResult& result) const {
    std::ostringstream out;
    out << std::fixed << std::setprecision(6);
    out << "{\n";
    out << "  \"bundle_id\": \"" << bundle.bundle_id << "\",\n";
    out << "  \"stable\": true,\n";
    out << "  \"stage_order\": [";
    for (size_t i = 0; i < result.stage_order.size(); ++i) {
        if (i) out << ", ";
        out << "\"" << result.stage_order[i] << "\"";
    }
    out << "],\n";
    out << "  \"variances\": {\n";
    for (size_t i = 0; i < result.variances.size(); ++i) {
        const auto& [id, val] = result.variances[i];
        out << "    \"" << id << "\": " << val;
        if (i + 1 < result.variances.size()) {
            out << ",";
        }
        out << "\n";
    }
    out << "  },\n";
    out << "  \"unstable_loops\": []\n";
    out << "}\n";
    return out.str();
}

}  // namespace cryogrid
