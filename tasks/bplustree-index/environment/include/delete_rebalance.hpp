#ifndef BPT_DELETE_REBALANCE_HPP
#define BPT_DELETE_REBALANCE_HPP

#include <cstdint>

#include "tree.hpp"

namespace bpt {

void tree_delete(Tree* t, std::uint64_t key);

}

#endif
