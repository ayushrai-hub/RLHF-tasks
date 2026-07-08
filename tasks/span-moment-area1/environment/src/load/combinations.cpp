#include "model/beam.hpp"
#include "model/load.hpp"

namespace beam::load {

Combination find_combination(const BeamModel& model, const std::string& name) {
    for (const auto& combo : model.combinations) {
        if (combo.name == name) {
            return combo;
        }
    }
    return Combination{name, {}};
}

}  // namespace beam::load
