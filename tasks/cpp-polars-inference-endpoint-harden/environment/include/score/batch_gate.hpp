#pragma once

#include <jsoncpp/json/json.h>
#include <string>

#include "score/ratified_policy.hpp"

struct GateResult {
    bool allowed = true;
    std::string reason;
};

class BatchGate {
public:
    GateResult screen(const Json::Value& rows, const Policy& policy);
};
