#ifndef BPT_SCAN_HPP
#define BPT_SCAN_HPP

#include <cstdint>
#include <string>
#include <vector>
#include <utility>

#include "tree.hpp"

namespace bpt {

std::vector<std::pair<std::uint64_t, std::string>> tree_range(const Tree* t,
                                                              std::uint64_t lo,
                                                              std::uint64_t hi);

std::string tree_dump(const Tree* t);

}

#endif
