#ifndef BPT_TREE_HPP
#define BPT_TREE_HPP

#include <cstdint>
#include <string>

#include "node.hpp"

namespace bpt {

struct Tree {
    Node* root = nullptr;
    std::uint16_t height = 1;
};

Tree* make_tree();
void free_tree(Tree* t);

bool tree_get(const Tree* t, std::uint64_t key, std::string& out);

}

#endif
