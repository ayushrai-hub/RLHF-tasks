#pragma once

#include <jsoncpp/json/json.h>
#include <string>

#include "score/ratified_policy.hpp"

class SidecarExec {
public:
    bool launch(const Json::Value& rows, const Policy& policy, Json::Value& features_out);
};
