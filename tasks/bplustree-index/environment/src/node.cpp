#include "node.hpp"

namespace bpt {

Node* make_leaf() {
    Node* n = new Node();
    n->leaf = true;
    n->next = nullptr;
    return n;
}

Node* make_internal() {
    Node* n = new Node();
    n->leaf = false;
    n->next = nullptr;
    return n;
}

void free_tree(Node* root) {
    if (root == nullptr) {
        return;
    }
    if (!root->leaf) {
        for (Node* c : root->children) {
            free_tree(c);
        }
    }
    delete root;
}

}
