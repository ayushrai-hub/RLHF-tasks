#pragma once

#include <jsoncpp/json/json.h>
#include <string>

struct Policy {
    int max_batch_rows = 128;
    std::string null_fill = "zero";
    std::string unknown_category = "bucket";
    std::string polars_pin = "0.20.31";
    int score_precision = 4;
};

class RatifiedPolicy {
public:
    Policy load(const std::string& dossier_path, const std::string& toml_path);
    std::string policy_seq(const Policy& policy) const;
};
