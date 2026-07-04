#include "tree.hpp"

namespace bpt {

Tree* make_tree() {
    Tree* t = new Tree();
    t->root = make_leaf();
    t->height = 1;
    return t;
}

void free_tree(Tree* t) {
    if (t == nullptr) {
        return;
    }
    free_tree(t->root);
    delete t;
}

bool tree_get(const Tree* t, std::uint64_t key, std::string& out) {
    (void)t;
    (void)key;
    (void)out;
    return false;
}

}
