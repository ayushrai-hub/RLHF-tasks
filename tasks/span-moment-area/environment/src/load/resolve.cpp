#include "model/load.hpp"

namespace beam::load {

ResolvedLoads superpose_cases(const BeamModel& model, const Combination& combo) {
    ResolvedLoads out;
    for (const auto& term : combo.terms) {
        const LoadCase* lc = nullptr;
        for (const auto& candidate : model.load_cases) {
            if (candidate.name == term.case_name) {
                lc = &candidate;
                break;
            }
        }
        if (lc == nullptr) {
            continue;
        }
        for (const auto& pf : lc->point_forces) {
            out.point_forces.push_back({pf.force_n * term.factor, pf.x_m});
        }
        for (const auto& pm : lc->point_moments) {
            out.point_moments.push_back({pm.moment_nm * term.factor, pm.x_m});
        }
        for (const auto& udl : lc->udls) {
            out.udls.push_back({udl.w_n_per_m * term.factor, udl.x0_m, udl.x1_m});
        }
    }
    return out;
}

}  // namespace beam::load
