#pragma once

#include <jsoncpp/json/json.h>
#include <string>

#include "score/ratified_policy.hpp"

class HttpService {
public:
    Json::Value handle_batch(const Json::Value& request, const Policy& policy,
                             const Json::Value& weights);
};
