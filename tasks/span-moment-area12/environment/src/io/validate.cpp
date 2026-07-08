#include "io/diagnostic.hpp"
#include "model/beam.hpp"

namespace beam::io {

void validate_model(const BeamModel& model) {
    if (model.nodes.size() < 2) {
        throw ParseError("at least two nodes required");
    }
    if (model.segments.empty()) {
        throw ParseError("at least one segment required");
    }
}

}  // namespace beam::io
