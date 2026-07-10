#pragma once

#include <string>

#include "score/ratified_policy.hpp"

class LockGuard {
public:
    bool probe(const std::string& lock_path, const Policy& policy);
    std::string lock_digest(const Policy& policy) const;
};
