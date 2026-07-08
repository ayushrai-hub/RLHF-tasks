#include "model/beam.hpp"

#include <string>

namespace beam::cache {

std::string envelope_cache_key(const CommittedState& state, const std::string& combination_name) {
    return state.model.beam_id + ":" + combination_name;
}

}  // namespace beam::cache
