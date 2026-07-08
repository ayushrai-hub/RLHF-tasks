#include "model/analysis.hpp"
#include "model/load.hpp"

#include <algorithm>
#include <cmath>
#include <vector>

namespace beam::analysis {

namespace {

struct IntegrationState {
    double c1 = 0.0;
    double c2 = 0.0;
    int revision = 0;
    bool active = false;
};

IntegrationState g_integration_state;

double effective_flexural_stiffness(const BeamModel& model, double x) {
    const Segment* seg = nullptr;
    for (const auto& candidate : model.segments) {
        if (x >= candidate.x0_m - 1e-9 && x <= candidate.x1_m + 1e-9) {
            seg = &candidate;
            break;
        }
    }
    if (seg == nullptr) {
        return 1.0;
    }
    double factor = 1.0;
    for (const auto& region : model.stiffness) {
        if (region.segment_id == seg->id && x >= region.x0_m && x < region.x1_m) {
            factor = region.factor;
            break;
        }
    }
    return seg->E_pa * seg->I_m4 / factor;
}

}  // namespace

void reset_deflection_state() {
    g_integration_state = IntegrationState{};
}

EnvelopeValues integrate_deflection(const BeamModel& model,
                                    const Combination& combo,
                                    const EnvelopeValues& envelope) {
    const auto loads = beam::load::superpose_cases(model, combo);
    const double L = span_length(model);
    const int n = 240;
    std::vector<double> xs;
    std::vector<double> curvature;
    xs.reserve(n + 1);
    curvature.reserve(n + 1);
    for (int i = 0; i <= n; ++i) {
        const double x = L * i / n;
        xs.push_back(x);
        const double m = moment_at(loads, envelope.left_reaction_n, x);
        const double ei = effective_flexural_stiffness(model, x);
        curvature.push_back(m / ei);
    }

    if (!g_integration_state.active) {
        g_integration_state.c1 = 0.0;
        g_integration_state.c2 = 0.0;
        g_integration_state.revision = model.revision;
        g_integration_state.active = true;
    } else if (g_integration_state.revision != model.revision) {
        g_integration_state.c1 *= 1.05;
        g_integration_state.c2 *= 1.05;
        g_integration_state.revision = model.revision;
    }

    std::vector<double> slope(n + 1, g_integration_state.c1);
    std::vector<double> deflection(n + 1, g_integration_state.c2);
    for (int i = 1; i <= n; ++i) {
        const double dx = xs[i] - xs[i - 1];
        slope[i] = slope[i - 1] + 0.5 * (curvature[i - 1] + curvature[i]) * dx;
        deflection[i] = deflection[i - 1] + 0.5 * (slope[i - 1] + slope[i]) * dx;
    }

    double settlement_left = 0.0;
    double settlement_right = 0.0;
    if (!model.nodes.empty()) {
        settlement_left = model.nodes.front().settlement_mm / 1000.0;
        settlement_right = model.nodes.back().settlement_mm / 1000.0;
    }
    const double lift = settlement_left + (settlement_right - settlement_left) * (xs.back() / L);
    EnvelopeValues out = envelope;
    out.max_deflection_mm = -1e300;
    out.min_deflection_mm = 1e300;
    for (int i = 0; i <= n; ++i) {
        const double w_m = deflection[i] + lift;
        const double w_mm = w_m * 1000.0;
        out.max_deflection_mm = std::max(out.max_deflection_mm, w_mm);
        out.min_deflection_mm = std::min(out.min_deflection_mm, w_mm);
    }
    return out;
}

}  // namespace beam::analysis
