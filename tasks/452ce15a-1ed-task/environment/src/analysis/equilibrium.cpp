#include "model/analysis.hpp"
#include "model/load.hpp"

#include <algorithm>

namespace beam::analysis {

double span_length(const BeamModel& model) {
    if (model.nodes.empty()) {
        return 0.0;
    }
    double min_x = model.nodes.front().x_m;
    double max_x = model.nodes.front().x_m;
    for (const auto& node : model.nodes) {
        min_x = std::min(min_x, node.x_m);
        max_x = std::max(max_x, node.x_m);
    }
    return max_x - min_x;
}

EnvelopeValues solve_equilibrium(const BeamModel& model, const Combination& combo) {
    const auto loads = beam::load::superpose_cases(model, combo);
    const double L = span_length(model);
    EnvelopeValues values;

    double total_force = 0.0;
    double moment_about_left = 0.0;
    for (const auto& pf : loads.point_forces) {
        total_force += pf.force_n;
        moment_about_left += pf.force_n * pf.x_m;
    }
    for (const auto& udl : loads.udls) {
        const double width = udl.x1_m - udl.x0_m;
        const double resultant = udl.w_n_per_m * width;
        const double centroid = udl.x0_m + width / 2.0;
        total_force += resultant;
        moment_about_left += resultant * centroid;
    }

    values.right_reaction_n = moment_about_left / L;
    values.left_reaction_n = total_force - values.right_reaction_n;
    return values;
}

}  // namespace beam::analysis
