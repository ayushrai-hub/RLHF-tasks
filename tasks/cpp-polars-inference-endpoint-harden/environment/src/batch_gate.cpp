#include "score/batch_gate.hpp"

#include <set>
#include <string>

namespace {
bool has_field(const Json::Value& row, const char* key) {
    return row.isMember(key) && !row[key].isNull();
}

bool approved_region(const std::string& value) {
    static const std::set<std::string> allowed = {"west", "east", "north", "south"};
    return allowed.count(value) > 0;
}

bool approved_channel(const std::string& value) {
    static const std::set<std::string> allowed = {"web", "phone", "retail"};
    return allowed.count(value) > 0;
}
}  // namespace

GateResult BatchGate::screen(const Json::Value& rows, const Policy& policy) {
    GateResult result;
    if (!rows.isArray()) {
        result.allowed = false;
        result.reason = "rows_not_array";
        return result;
    }
    if (static_cast<int>(rows.size()) > policy.max_batch_rows) {
        result.allowed = false;
        result.reason = "batch_too_large";
        return result;
    }
    for (const auto& row : rows) {
        if (!has_field(row, "row_id") || !has_field(row, "region") || !has_field(row, "channel")) {
            result.allowed = false;
            result.reason = "missing_required";
            return result;
        }
        std::string region = row["region"].asString();
        std::string channel = row["channel"].asString();
        if (!approved_region(region)) {
            if (policy.unknown_category == "bucket") {
                continue;
            }
            result.allowed = false;
            result.reason = "unknown_region";
            return result;
        }
        if (!approved_channel(channel)) {
            if (policy.unknown_category == "bucket") {
                continue;
            }
            result.allowed = false;
            result.reason = "unknown_channel";
            return result;
        }
    }
    return result;
}
