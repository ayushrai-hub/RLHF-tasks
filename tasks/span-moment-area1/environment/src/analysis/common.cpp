#include "model/analysis.hpp"
#include "model/load.hpp"

namespace beam::analysis {

double moment_at(const beam::load::ResolvedLoads& loads, double reaction_left, double x) {
    double m = reaction_left * x;
    for (const auto& pf : loads.point_forces) {
        if (x + 1e-12 >= pf.x_m) {
            m -= pf.force_n * (x - pf.x_m);
        }
    }
    for (const auto& pm : loads.point_moments) {
        if (x + 1e-12 >= pm.x_m) {
            m += pm.moment_nm;
        }
    }
    for (const auto& udl : loads.udls) {
        if (x > udl.x0_m) {
            const double dx = std::min(x, udl.x1_m) - udl.x0_m;
            m -= 0.5 * udl.w_n_per_m * dx * dx;
        }
    }
    return m;
}

double shear_at(const beam::load::ResolvedLoads& loads, double reaction_left, double x) {
    double v = reaction_left;
    for (const auto& pf : loads.point_forces) {
        if (x + 1e-12 >= pf.x_m) {
            v -= pf.force_n;
        }
    }
    for (const auto& udl : loads.udls) {
        if (x > udl.x0_m) {
            const double dx = std::min(x, udl.x1_m) - udl.x0_m;
            v -= udl.w_n_per_m * dx;
        }
    }
    return v;
}

}  // namespace beam::analysis
