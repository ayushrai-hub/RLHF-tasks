#include "scan.hpp"

namespace bpt {

std::vector<std::pair<std::uint64_t, std::string>> tree_range(const Tree* t,
                                                              std::uint64_t lo,
                                                              std::uint64_t hi) {
    (void)t;
    (void)lo;
    (void)hi;
    return {};
}

std::string tree_dump(const Tree* t) {
    (void)t;
    return std::string();
}

}
