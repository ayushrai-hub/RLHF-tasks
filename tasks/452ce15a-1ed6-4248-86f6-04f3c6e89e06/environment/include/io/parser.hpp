#pragma once

#include "model/beam.hpp"

#include <string>

namespace beam::io {

struct ParsedStage {
    BeamModel model;
    StageDirective directive;
};

ParsedStage parse_stage_file(const std::string& path);

}  // namespace beam::io
