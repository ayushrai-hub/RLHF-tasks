#!/bin/bash
set -euo pipefail

cd /app

cat > src/tree.cpp <<'EOF'
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
    Node* n = t->root;
    if (n == nullptr) {
        return false;
    }
    while (!n->leaf) {
        std::size_t i = 0;
        while (i < n->keys.size() && key >= n->keys[i]) {
            ++i;
        }
        n = n->children[i];
    }
    for (std::size_t i = 0; i < n->keys.size(); ++i) {
        if (n->keys[i] == key) {
            out = n->values[i];
            return true;
        }
    }
    return false;
}

}
EOF

cat > src/insert.cpp <<'EOF'
#include "insert.hpp"
#include "page.hpp"

#include <algorithm>

namespace bpt {

struct Split {
    bool did = false;
    std::uint64_t sep = 0;
    Node* right = nullptr;
};

static std::size_t leaf_pos(const Node* n, std::uint64_t key) {
    std::size_t i = 0;
    while (i < n->keys.size() && n->keys[i] < key) {
        ++i;
    }
    return i;
}

static std::size_t child_index(const Node* n, std::uint64_t key) {
    std::size_t i = 0;
    while (i < n->keys.size() && key >= n->keys[i]) {
        ++i;
    }
    return i;
}

static Split split_leaf(Node* n) {
    Node* right = make_leaf();
    std::size_t s = 3;
    for (std::size_t i = s; i < n->keys.size(); ++i) {
        right->keys.push_back(n->keys[i]);
        right->values.push_back(n->values[i]);
    }
    n->keys.resize(s);
    n->values.resize(s);
    right->next = n->next;
    n->next = right;
    Split sp;
    sp.did = true;
    sp.sep = right->keys.front();
    sp.right = right;
    return sp;
}

static Split split_internal(Node* n) {
    Node* right = make_internal();
    std::size_t m = 2;
    std::uint64_t sep = n->keys[m];
    for (std::size_t i = m + 1; i < n->keys.size(); ++i) {
        right->keys.push_back(n->keys[i]);
    }
    for (std::size_t i = m + 1; i < n->children.size(); ++i) {
        right->children.push_back(n->children[i]);
    }
    n->keys.resize(m);
    n->children.resize(m + 1);
    Split sp;
    sp.did = true;
    sp.sep = sep;
    sp.right = right;
    return sp;
}

static Split insert_rec(Node* n, std::uint64_t key, const std::string& value) {
    if (n->leaf) {
        std::size_t i = leaf_pos(n, key);
        if (i < n->keys.size() && n->keys[i] == key) {
            n->values[i] = value;
            return Split();
        }
        n->keys.insert(n->keys.begin() + i, key);
        n->values.insert(n->values.begin() + i, value);
        if (n->keys.size() > LEAF_CAP) {
            return split_leaf(n);
        }
        return Split();
    }
    std::size_t ci = child_index(n, key);
    Split child = insert_rec(n->children[ci], key, value);
    if (!child.did) {
        return Split();
    }
    n->keys.insert(n->keys.begin() + ci, child.sep);
    n->children.insert(n->children.begin() + ci + 1, child.right);
    if (n->keys.size() > INT_FANOUT - 1) {
        return split_internal(n);
    }
    return Split();
}

void tree_insert(Tree* t, std::uint64_t key, const std::string& value) {
    Split sp = insert_rec(t->root, key, value);
    if (sp.did) {
        Node* nr = make_internal();
        nr->keys.push_back(sp.sep);
        nr->children.push_back(t->root);
        nr->children.push_back(sp.right);
        t->root = nr;
        t->height = static_cast<std::uint16_t>(t->height + 1);
    }
}

}
EOF

cat > src/serialize.cpp <<'EOF'
#include "serialize.hpp"

#include <cstdio>
#include <cstring>
#include <map>
#include <queue>
#include <vector>

#include "page.hpp"

namespace bpt {

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

bool serialize_tree(const Tree* t, const std::string& path) {
    std::vector<Node*> order;
    assign_ids(t, order);
    std::uint32_t page_count = static_cast<std::uint32_t>(order.size() + 1);
    std::vector<unsigned char> buf(static_cast<std::size_t>(page_count) * PAGE_SIZE, 0);

    unsigned char* sb = buf.data();
    std::memcpy(sb, "BPT1", 4);
    put_u32(sb + 4, SB_PAGE_SIZE);
    put_u32(sb + 8, t->root ? t->root->page_id : 0);
    put_u32(sb + 12, page_count);
    put_u16(sb + 16, static_cast<std::uint16_t>(LEAF_CAP));
    put_u16(sb + 18, static_cast<std::uint16_t>(INT_FANOUT));
    put_u16(sb + 20, t->height);

    for (Node* n : order) {
        unsigned char* p = buf.data() + static_cast<std::size_t>(n->page_id) * PAGE_SIZE;
        put_u32(p + 0, n->page_id);
        p[4] = n->leaf ? 1 : 0;
        put_u16(p + 5, static_cast<std::uint16_t>(n->keys.size()));
        p[7] = 0;
        std::size_t off = 8;
        if (n->leaf) {
            std::uint32_t nx = n->next ? n->next->page_id : NO_PAGE;
            put_u32(p + off, nx);
            off += 4;
            for (std::size_t i = 0; i < n->keys.size(); ++i) {
                put_u64(p + off, n->keys[i]);
                off += 8;
                p[off] = static_cast<unsigned char>(n->values[i].size());
                off += 1;
                std::memcpy(p + off, n->values[i].data(), n->values[i].size());
                off += n->values[i].size();
            }
        } else {
            put_u32(p + off, n->children[0]->page_id);
            off += 4;
            for (std::size_t i = 0; i < n->keys.size(); ++i) {
                put_u64(p + off, n->keys[i]);
                off += 8;
                put_u32(p + off, n->children[i + 1]->page_id);
                off += 4;
            }
        }
    }

    FILE* f = std::fopen(path.c_str(), "wb");
    if (f == nullptr) {
        return false;
    }
    std::size_t wrote = std::fwrite(buf.data(), 1, buf.size(), f);
    std::fclose(f);
    return wrote == buf.size();
}

Tree* deserialize_tree(const std::string& path) {
    FILE* f = std::fopen(path.c_str(), "rb");
    if (f == nullptr) {
        return nullptr;
    }
    std::fseek(f, 0, SEEK_END);
    long sz = std::ftell(f);
    std::fseek(f, 0, SEEK_SET);
    if (sz < static_cast<long>(PAGE_SIZE)) {
        std::fclose(f);
        return nullptr;
    }
    std::vector<unsigned char> buf(static_cast<std::size_t>(sz));
    std::size_t got = std::fread(buf.data(), 1, buf.size(), f);
    std::fclose(f);
    if (got != buf.size()) {
        return nullptr;
    }
    const unsigned char* sb = buf.data();
    if (std::memcmp(sb, "BPT1", 4) != 0) {
        return nullptr;
    }
    std::uint32_t root_id = get_u32(sb + 8);
    std::uint32_t page_count = get_u32(sb + 12);
    std::uint16_t height = get_u16(sb + 20);

    std::map<std::uint32_t, Node*> nodes;
    for (std::uint32_t id = 1; id < page_count; ++id) {
        const unsigned char* p = buf.data() + static_cast<std::size_t>(id) * PAGE_SIZE;
        unsigned char flags = p[4];
        Node* n = flags == 1 ? make_leaf() : make_internal();
        n->page_id = id;
        nodes[id] = n;
    }
    for (std::uint32_t id = 1; id < page_count; ++id) {
        const unsigned char* p = buf.data() + static_cast<std::size_t>(id) * PAGE_SIZE;
        Node* n = nodes[id];
        std::uint16_t nk = get_u16(p + 5);
        std::size_t off = 8;
        if (n->leaf) {
            std::uint32_t nx = get_u32(p + off);
            off += 4;
            n->next = (nx == NO_PAGE) ? nullptr : nodes[nx];
            for (std::uint16_t i = 0; i < nk; ++i) {
                std::uint64_t k = get_u64(p + off);
                off += 8;
                std::uint8_t vl = p[off];
                off += 1;
                std::string v(reinterpret_cast<const char*>(p + off), vl);
                off += vl;
                n->keys.push_back(k);
                n->values.push_back(v);
            }
        } else {
            std::uint32_t c0 = get_u32(p + off);
            off += 4;
            n->children.push_back(nodes[c0]);
            for (std::uint16_t i = 0; i < nk; ++i) {
                std::uint64_t k = get_u64(p + off);
                off += 8;
                std::uint32_t ci = get_u32(p + off);
                off += 4;
                n->keys.push_back(k);
                n->children.push_back(nodes[ci]);
            }
        }
    }
    Tree* t = new Tree();
    t->root = (root_id == 0) ? nullptr : nodes[root_id];
    t->height = height;
    return t;
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

std::vector<std::pair<std::uint64_t, std::string>> tree_range(const Tree* t,
                                                              std::uint64_t lo,
                                                              std::uint64_t hi) {
    (void)t;
    (void)lo;
    (void)hi;
    return {};
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

cat > src/io.cpp <<'EOF'
#include "io.hpp"

#include <fstream>
#include <sstream>
#include <string>

#include "insert.hpp"
#include "delete_rebalance.hpp"

namespace bpt {

bool read_ops(const std::string& path, std::vector<Op>& out) {
    std::ifstream in(path);
    if (!in.is_open()) {
        return false;
    }
    std::string line;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        std::istringstream ls(line);
        std::string tok;
        if (!(ls >> tok)) {
            continue;
        }
        Op op;
        if (tok == "I") {
            std::string ks, vs;
            if (!(ls >> ks) || !(ls >> vs)) {
                return false;
            }
            if (vs.size() < 1 || vs.size() > 255) {
                return false;
            }
            op.insert = true;
            op.key = std::stoull(ks);
            op.value = vs;
        } else if (tok == "D") {
            std::string ks;
            if (!(ls >> ks)) {
                return false;
            }
            op.insert = false;
            op.key = std::stoull(ks);
        } else {
            return false;
        }
        out.push_back(op);
    }
    return true;
}

void apply_ops(Tree* t, const std::vector<Op>& ops) {
    for (const Op& op : ops) {
        if (op.insert) {
            tree_insert(t, op.key, op.value);
        } else {
            tree_delete(t, op.key);
        }
    }
}

}
EOF

cat > src/cli.cpp <<'EOF'
#include "cli.hpp"

#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include "io.hpp"
#include "scan.hpp"
#include "serialize.hpp"
#include "tree.hpp"

namespace bpt {

static bool parse_u64(const char* s, std::uint64_t& out) {
    if (s == nullptr || *s == '\0') {
        return false;
    }
    std::uint64_t v = 0;
    for (const char* p = s; *p; ++p) {
        if (*p < '0' || *p > '9') {
            return false;
        }
        v = v * 10 + static_cast<std::uint64_t>(*p - '0');
    }
    out = v;
    return true;
}

static int do_build(int argc, char** argv) {
    if (argc != 5) {
        return 1;
    }
    std::string ops_path = argv[2];
    if (std::string(argv[3]) != "--out") {
        return 1;
    }
    std::string out_path = argv[4];
    std::vector<Op> ops;
    if (!read_ops(ops_path, ops)) {
        return 1;
    }
    Tree* t = make_tree();
    apply_ops(t, ops);
    bool ok = serialize_tree(t, out_path);
    free_tree(t);
    return ok ? 0 : 1;
}

static int do_apply(int argc, char** argv) {
    if (argc != 5) {
        return 1;
    }
    Tree* t = deserialize_tree(argv[2]);
    if (t == nullptr) {
        return 1;
    }
    std::vector<Op> ops;
    if (!read_ops(argv[3], ops)) {
        free_tree(t);
        return 1;
    }
    apply_ops(t, ops);
    bool ok = serialize_tree(t, argv[4]);
    free_tree(t);
    return ok ? 0 : 1;
}

static int do_get(int argc, char** argv) {
    if (argc != 4) {
        return 1;
    }
    std::uint64_t key;
    if (!parse_u64(argv[3], key)) {
        return 1;
    }
    Tree* t = deserialize_tree(argv[2]);
    if (t == nullptr) {
        return 1;
    }
    std::string v;
    bool found = tree_get(t, key, v);
    if (found) {
        std::fwrite(v.data(), 1, v.size(), stdout);
        std::fputc('\n', stdout);
    } else {
        std::fputs("NOT-FOUND\n", stdout);
    }
    free_tree(t);
    return 0;
}

static int do_range(int argc, char** argv) {
    if (argc != 5) {
        return 1;
    }
    std::uint64_t lo, hi;
    if (!parse_u64(argv[3], lo) || !parse_u64(argv[4], hi)) {
        return 1;
    }
    Tree* t = deserialize_tree(argv[2]);
    if (t == nullptr) {
        return 1;
    }
    auto rows = tree_range(t, lo, hi);
    for (const auto& r : rows) {
        std::string line = std::to_string(r.first);
        line += "\t";
        line += r.second;
        line += "\n";
        std::fwrite(line.data(), 1, line.size(), stdout);
    }
    free_tree(t);
    return 0;
}

static int do_dump(int argc, char** argv) {
    if (argc != 3) {
        return 1;
    }
    Tree* t = deserialize_tree(argv[2]);
    if (t == nullptr) {
        return 1;
    }
    std::string s = tree_dump(t);
    std::fwrite(s.data(), 1, s.size(), stdout);
    free_tree(t);
    return 0;
}

int run_cli(int argc, char** argv) {
    if (argc < 2) {
        return 1;
    }
    std::string cmd = argv[1];
    if (cmd == "build") {
        return do_build(argc, argv);
    }
    if (cmd == "apply") {
        return do_apply(argc, argv);
    }
    if (cmd == "get") {
        return do_get(argc, argv);
    }
    if (cmd == "range") {
        return do_range(argc, argv);
    }
    if (cmd == "dump") {
        return do_dump(argc, argv);
    }
    return 1;
}

}
EOF

make clean
make
