#include "model/analysis.hpp"
#include "model/load.hpp"

namespace beam::analysis {

EnvelopeValues scan_extrema(const BeamModel& model,
                            const Combination& combo,
                            const EnvelopeValues& reactions) {
    return assemble_piecewise(model, combo, reactions);
}

}  // namespace beam::analysis
