#include "model/analysis.hpp"
#include "model/load.hpp"

namespace beam::analysis {

double curvature_at(const BeamModel& model,
                    const Combination& combo,
                    const EnvelopeValues& reactions,
                    double x) {
    const auto loads = beam::load::superpose_cases(model, combo);
    const double m = moment_at(loads, reactions.left_reaction_n, x);
    double ei = 1.0;
    for (const auto& seg : model.segments) {
        if (x >= seg.x0_m && x <= seg.x1_m) {
            ei = seg.E_pa * seg.I_m4;
            break;
        }
    }
    return m / ei;
}

}  // namespace beam::analysis
