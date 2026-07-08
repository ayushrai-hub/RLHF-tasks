#pragma once

#include "model/beam.hpp"

namespace beam::stage {

struct StageOutcome {
    bool accepted = false;
    CommittedState state;
};

CommittedState process_journal(const std::vector<std::string>& stage_paths);

}  // namespace beam::stage
