#pragma once

#include "model/beam.hpp"
#include "model/load.hpp"

namespace beam::analysis {

double span_length(const BeamModel& model);
double moment_at(const beam::load::ResolvedLoads& loads, double reaction_left, double x);
double shear_at(const beam::load::ResolvedLoads& loads, double reaction_left, double x);
EnvelopeValues solve_equilibrium(const BeamModel& model, const Combination& combo);
EnvelopeValues assemble_piecewise(const BeamModel& model,
                                  const Combination& combo,
                                  const EnvelopeValues& reactions);
EnvelopeValues integrate_deflection(const BeamModel& model,
                                    const Combination& combo,
                                    const EnvelopeValues& envelope);
void reset_deflection_state();

}  // namespace beam::analysis
