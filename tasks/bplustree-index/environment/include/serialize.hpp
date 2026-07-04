#ifndef BPT_SERIALIZE_HPP
#define BPT_SERIALIZE_HPP

#include <string>

#include "tree.hpp"

namespace bpt {

bool serialize_tree(const Tree* t, const std::string& path);
Tree* deserialize_tree(const std::string& path);

}

#endif
