#pragma once

#include "model/beam.hpp"

#include <map>
#include <string>

namespace beam::model {

std::map<std::string, SegmentFrame> committed_segment_frames(const BeamModel& model);
void apply_amendment(BeamModel& committed,
                     const BeamModel& pending,
                     const StageDirective& directive,
                     const std::map<std::string, SegmentFrame>& superseded_frames);

}  // namespace beam::model
