#ifndef BPT_NODE_HPP
#define BPT_NODE_HPP

#include <cstdint>
#include <string>
#include <vector>

namespace bpt {

struct Node {
    bool leaf = true;
    std::vector<std::uint64_t> keys;
    std::vector<Node*> children;
    std::vector<std::string> values;
    Node* next = nullptr;
    std::uint32_t page_id = 0;
};

Node* make_leaf();
Node* make_internal();
void free_tree(Node* root);

}

#endif
