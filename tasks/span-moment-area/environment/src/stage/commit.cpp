#include "model/stage.hpp"

namespace beam::stage {

bool integrity_ok(const StageDirective& directive) {
    return !directive.integrity.empty();
}

}  // namespace beam::stage
