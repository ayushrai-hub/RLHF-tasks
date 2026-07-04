#include "io.hpp"

#include "insert.hpp"
#include "delete_rebalance.hpp"

namespace bpt {

bool read_ops(const std::string& path, std::vector<Op>& out) {
    (void)path;
    (void)out;
    return false;
}

void apply_ops(Tree* t, const std::vector<Op>& ops) {
    (void)t;
    (void)ops;
}

}
