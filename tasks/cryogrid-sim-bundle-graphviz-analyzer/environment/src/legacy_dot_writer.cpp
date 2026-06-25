#include "cryogrid/legacy_dot_writer.hpp"

#include <string>

namespace cryogrid {

std::string LegacyDotWriter::writeMinimal() const {
    return "digraph Legacy { a -> b; }\n";
}

}  // namespace cryogrid
