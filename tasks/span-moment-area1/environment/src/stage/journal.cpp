#include "model/stage.hpp"

#include "io/parser.hpp"
#include "model/amend.hpp"
#include "model/analysis.hpp"

namespace beam::stage {

CommittedState process_journal(const std::vector<std::string>& stage_paths) {
    CommittedState committed;
    bool initialized = false;

    for (const auto& path : stage_paths) {
        const auto stage = beam::io::parse_stage_file(path);
        if (!initialized) {
            committed.model = stage.model;
            committed.committed_revision = stage.model.revision;
            committed.amendment_generation = 1;
            committed.accepted_stages = 1;
            initialized = true;
            continue;
        }

        if (!stage.directive.is_amendment) {
            committed.model = stage.model;
            committed.committed_revision = stage.model.revision;
            ++committed.amendment_generation;
            ++committed.accepted_stages;
            continue;
        }

        if (!stage.directive.accept) {
            ++committed.rejected_stages;
            continue;
        }

        const auto superseded = beam::model::committed_segment_frames(committed.model);
        beam::model::apply_amendment(committed.model, stage.model, stage.directive, superseded);
        committed.committed_revision = stage.model.revision;
        ++committed.amendment_generation;
        ++committed.accepted_stages;
    }

    return committed;
}

}  // namespace beam::stage
