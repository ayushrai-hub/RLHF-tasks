#!/bin/bash
set -euo pipefail

cd /app

cat > src/delete_rebalance.cpp <<'EOF'
#include "delete_rebalance.hpp"

namespace bpt {

static const std::size_t LEAF_MIN = 2;
static const std::size_t INT_MIN_KEYS = 2;

static std::size_t child_index(const Node* n, std::uint64_t key) {
    std::size_t i = 0;
    while (i < n->keys.size() && key >= n->keys[i]) {
        ++i;
    }
    return i;
}

static void fix_child(Node* p, std::size_t i) {
    Node* c = p->children[i];
    bool under = c->leaf ? (c->keys.size() < LEAF_MIN)
                         : (c->keys.size() < INT_MIN_KEYS);
    if (!under) {
        return;
    }
    Node* left = (i > 0) ? p->children[i - 1] : nullptr;
    Node* right = (i + 1 < p->children.size()) ? p->children[i + 1] : nullptr;

    if (c->leaf) {
        if (left && left->keys.size() > LEAF_MIN) {
            c->keys.insert(c->keys.begin(), left->keys.back());
            c->values.insert(c->values.begin(), left->values.back());
            left->keys.pop_back();
            left->values.pop_back();
            p->keys[i - 1] = c->keys.front();
            return;
        }
        if (right && right->keys.size() > LEAF_MIN) {
            c->keys.push_back(right->keys.front());
            c->values.push_back(right->values.front());
            right->keys.erase(right->keys.begin());
            right->values.erase(right->values.begin());
            p->keys[i] = right->keys.front();
            return;
        }
        if (left) {
            for (std::size_t k = 0; k < c->keys.size(); ++k) {
                left->keys.push_back(c->keys[k]);
                left->values.push_back(c->values[k]);
            }
            left->next = c->next;
            delete c;
            p->keys.erase(p->keys.begin() + (i - 1));
            p->children.erase(p->children.begin() + i);
            return;
        }
        for (std::size_t k = 0; k < right->keys.size(); ++k) {
            c->keys.push_back(right->keys[k]);
            c->values.push_back(right->values[k]);
        }
        c->next = right->next;
        delete right;
        p->keys.erase(p->keys.begin() + i);
        p->children.erase(p->children.begin() + (i + 1));
        return;
    }

    if (left && left->keys.size() > INT_MIN_KEYS) {
        c->keys.insert(c->keys.begin(), p->keys[i - 1]);
        c->children.insert(c->children.begin(), left->children.back());
        left->children.pop_back();
        p->keys[i - 1] = left->keys.back();
        left->keys.pop_back();
        return;
    }
    if (right && right->keys.size() > INT_MIN_KEYS) {
        c->keys.push_back(p->keys[i]);
        c->children.push_back(right->children.front());
        right->children.erase(right->children.begin());
        p->keys[i] = right->keys.front();
        right->keys.erase(right->keys.begin());
        return;
    }
    if (left) {
        left->keys.push_back(p->keys[i - 1]);
        for (std::size_t k = 0; k < c->keys.size(); ++k) {
            left->keys.push_back(c->keys[k]);
        }
        for (std::size_t k = 0; k < c->children.size(); ++k) {
            left->children.push_back(c->children[k]);
        }
        delete c;
        p->keys.erase(p->keys.begin() + (i - 1));
        p->children.erase(p->children.begin() + i);
        return;
    }
    c->keys.push_back(p->keys[i]);
    for (std::size_t k = 0; k < right->keys.size(); ++k) {
        c->keys.push_back(right->keys[k]);
    }
    for (std::size_t k = 0; k < right->children.size(); ++k) {
        c->children.push_back(right->children[k]);
    }
    delete right;
    p->keys.erase(p->keys.begin() + i);
    p->children.erase(p->children.begin() + (i + 1));
}

static void delete_rec(Node* n, std::uint64_t key) {
    if (n->leaf) {
        std::size_t i = 0;
        while (i < n->keys.size() && n->keys[i] < key) {
            ++i;
        }
        if (i < n->keys.size() && n->keys[i] == key) {
            n->keys.erase(n->keys.begin() + i);
            n->values.erase(n->values.begin() + i);
        }
        return;
    }
    std::size_t ci = child_index(n, key);
    delete_rec(n->children[ci], key);
    fix_child(n, ci);
}

void tree_delete(Tree* t, std::uint64_t key) {
    delete_rec(t->root, key);
    if (!t->root->leaf && t->root->keys.empty()) {
        Node* only = t->root->children.front();
        delete t->root;
        t->root = only;
        t->height = static_cast<std::uint16_t>(t->height - 1);
    }
}

}
EOF

cat > src/scan.cpp <<'EOF'
#include "scan.hpp"

#include <queue>
#include <sstream>
#include <vector>

#include "page.hpp"

namespace bpt {

static Node* leftmost_leaf(const Tree* t, std::uint64_t lo) {
    Node* n = t->root;
    if (n == nullptr) {
        return nullptr;
    }
    while (!n->leaf) {
        std::size_t i = 0;
        while (i < n->keys.size() && lo >= n->keys[i]) {
            ++i;
        }
        n = n->children[i];
    }
    return n;
}

std::vector<std::pair<std::uint64_t, std::string>> tree_range(const Tree* t,
                                                              std::uint64_t lo,
                                                              std::uint64_t hi) {
    std::vector<std::pair<std::uint64_t, std::string>> out;
    if (lo > hi) {
        return out;
    }
    Node* n = leftmost_leaf(t, lo);
    while (n != nullptr) {
        bool done = false;
        for (std::size_t i = 0; i < n->keys.size(); ++i) {
            std::uint64_t k = n->keys[i];
            if (k < lo) {
                continue;
            }
            if (k > hi) {
                done = true;
                break;
            }
            out.push_back({k, n->values[i]});
        }
        if (done) {
            break;
        }
        n = n->next;
    }
    return out;
}

static void assign_ids(const Tree* t, std::vector<Node*>& order) {
    order.clear();
    if (t->root == nullptr) {
        return;
    }
    std::queue<Node*> q;
    q.push(t->root);
    std::uint32_t next = 1;
    while (!q.empty()) {
        Node* n = q.front();
        q.pop();
        n->page_id = next++;
        order.push_back(n);
        if (!n->leaf) {
            for (Node* c : n->children) {
                q.push(c);
            }
        }
    }
}

std::string tree_dump(const Tree* t) {
    std::vector<Node*> order;
    assign_ids(t, order);
    std::ostringstream os;
    os << "height " << t->height << "\n";
    os << "root " << (t->root ? t->root->page_id : 0) << "\n";
    for (Node* n : order) {
        if (n->leaf) {
            os << "leaf page " << n->page_id << " next ";
            if (n->next) {
                os << n->next->page_id;
            } else {
                os << "-";
            }
            os << " entries";
            for (std::size_t i = 0; i < n->keys.size(); ++i) {
                os << " " << n->keys[i] << ":" << n->values[i];
            }
            os << "\n";
        } else {
            os << "internal page " << n->page_id << " keys";
            for (std::size_t i = 0; i < n->keys.size(); ++i) {
                os << " " << n->keys[i];
            }
            os << " children";
            for (std::size_t i = 0; i < n->children.size(); ++i) {
                os << " " << n->children[i]->page_id;
            }
            os << "\n";
        }
    }
    return os.str();
}

}
EOF

make clean
make
