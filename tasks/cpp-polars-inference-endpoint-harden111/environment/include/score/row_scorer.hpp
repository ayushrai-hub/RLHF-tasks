#pragma once

#include <jsoncpp/json/json.h>
#include <string>

#include "score/ratified_policy.hpp"

class RowScorer {
public:
    double blend(const Json::Value& features, const Json::Value& weights, const Policy& policy);
    std::string feature_digest(const Json::Value& features) const;
};
