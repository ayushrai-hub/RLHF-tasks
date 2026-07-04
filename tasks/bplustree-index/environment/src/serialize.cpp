#include "serialize.hpp"

namespace bpt {

bool serialize_tree(const Tree* t, const std::string& path) {
    (void)t;
    (void)path;
    return false;
}

Tree* deserialize_tree(const std::string& path) {
    (void)path;
    return nullptr;
}

}
