#ifndef BPT_IO_HPP
#define BPT_IO_HPP

#include <cstdint>
#include <string>
#include <vector>

#include "tree.hpp"

namespace bpt {

struct Op {
    bool insert = true;
    std::uint64_t key = 0;
    std::string value;
};

bool read_ops(const std::string& path, std::vector<Op>& out);
void apply_ops(Tree* t, const std::vector<Op>& ops);

}

#endif
