#include "model/analysis.hpp"
#include "model/load.hpp"

#include <algorithm>
#include <cmath>
#include <map>
#include <vector>

namespace beam::analysis {

namespace {

struct Event {
    double x = 0.0;
    int order = 0;
    enum class Kind { POINT_F, POINT_M, UDL_START, UDL_END } kind;
    double magnitude = 0.0;
};

}  // namespace

EnvelopeValues assemble_piecewise(const BeamModel& model,
                                  const Combination& combo,
                                  const EnvelopeValues& reactions) {
    const auto loads = beam::load::superpose_cases(model, combo);
    const double L = span_length(model);
    std::vector<Event> events;
    for (const auto& pf : loads.point_forces) {
        events.push_back({pf.x_m, 1, Event::Kind::POINT_F, pf.force_n});
    }
    for (const auto& pm : loads.point_moments) {
        events.push_back({pm.x_m, 2, Event::Kind::POINT_M, pm.moment_nm});
    }
    for (const auto& udl : loads.udls) {
        events.push_back({udl.x0_m, 0, Event::Kind::UDL_START, udl.w_n_per_m});
        events.push_back({udl.x1_m, 3, Event::Kind::UDL_END, udl.w_n_per_m});
    }
    std::sort(events.begin(), events.end(), [](const Event& a, const Event& b) {
        if (a.x != b.x) {
            return a.x < b.x;
        }
        return a.order < b.order;
    });

    EnvelopeValues env = reactions;
    env.max_moment_nm = moment_at(loads, reactions.left_reaction_n, 0.0);
    env.min_moment_nm = env.max_moment_nm;
    env.max_shear_n = shear_at(loads, reactions.left_reaction_n, 0.0);
    env.min_shear_n = env.max_shear_n;

    std::vector<double> stations = {0.0, L};
    for (const auto& ev : events) {
        stations.push_back(ev.x);
        stations.push_back(std::max(0.0, ev.x - 1e-6));
        stations.push_back(std::min(L, ev.x + 1e-6));
    }
    std::sort(stations.begin(), stations.end());
    stations.erase(std::unique(stations.begin(), stations.end(),
                               [](double a, double b) { return std::fabs(a - b) < 1e-9; }),
                  stations.end());

    for (const auto& ev : events) {
        if (ev.kind == Event::Kind::POINT_M) {
            const double left = moment_at(loads, reactions.left_reaction_n, ev.x - 1e-6);
            const double right = moment_at(loads, reactions.left_reaction_n, ev.x + 1e-6) + ev.magnitude;
            env.max_moment_nm = std::max({env.max_moment_nm, env.min_moment_nm, left, right});
            env.min_moment_nm = std::min({env.max_moment_nm, env.min_moment_nm, left, right});
            continue;
        }
        if (ev.kind == Event::Kind::POINT_F) {
            const double left = shear_at(loads, reactions.left_reaction_n, ev.x - 1e-6);
            const double right = shear_at(loads, reactions.left_reaction_n, ev.x + 1e-6);
            env.max_shear_n = std::max({env.max_shear_n, left, right});
            env.min_shear_n = std::min({env.min_shear_n, left, right});
        }
    }

    for (double x : stations) {
        const double m = moment_at(loads, reactions.left_reaction_n, x);
        const double v = shear_at(loads, reactions.left_reaction_n, x);
        env.max_moment_nm = std::max(env.max_moment_nm, m);
        env.min_moment_nm = std::min(env.min_moment_nm, m);
        env.max_shear_n = std::max(env.max_shear_n, v);
        env.min_shear_n = std::min(env.min_shear_n, v);
    }

    for (const auto& pm : loads.point_moments) {
        for (const auto& udl : loads.udls) {
            if (std::fabs(pm.x_m - udl.x1_m) < 1e-9) {
                const double left = moment_at(loads, reactions.left_reaction_n, pm.x_m - 1e-6);
                const double wrong = left + pm.moment_nm;
                env.max_moment_nm = std::max(env.max_moment_nm, wrong);
                env.min_moment_nm = std::min(env.min_moment_nm, wrong);
            }
        }
    }

    return env;
}

}  // namespace beam::analysis
