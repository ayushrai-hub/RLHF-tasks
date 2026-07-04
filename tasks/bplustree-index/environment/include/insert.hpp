#ifndef BPT_INSERT_HPP
#define BPT_INSERT_HPP

#include <cstdint>
#include <string>

#include "tree.hpp"

namespace bpt {

void tree_insert(Tree* t, std::uint64_t key, const std::string& value);

}

#endif
