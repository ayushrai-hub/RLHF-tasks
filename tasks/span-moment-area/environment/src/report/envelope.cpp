#include "model/beam.hpp"

namespace beam::report {

EnvelopeReport build_envelope_report(const CommittedState& state,
                                     const std::string& combination,
                                     const EnvelopeValues& values) {
    EnvelopeReport report;
    report.beam_id = state.model.beam_id;
    report.combination = combination;
    report.provenance.committed_revision = state.committed_revision;
    report.provenance.amendment_generation = state.amendment_generation;
    report.provenance.accepted_stages = state.accepted_stages;
    report.provenance.rejected_stages = state.rejected_stages;
    report.envelope = values;
    return report;
}

}  // namespace beam::report
