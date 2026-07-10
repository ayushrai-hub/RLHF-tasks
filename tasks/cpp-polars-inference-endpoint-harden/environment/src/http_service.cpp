#include "score/http_service.hpp"

#include <algorithm>
#include <cmath>
#include <vector>

#include "score/batch_gate.hpp"
#include "score/lock_guard.hpp"
#include "score/row_scorer.hpp"
#include "score/sidecar_exec.hpp"

Json::Value HttpService::handle_batch(const Json::Value& request, const Policy& policy,
                                      const Json::Value& weights) {
    Json::Value response(Json::objectValue);
    response["api_version"] = "1";
    RatifiedPolicy policy_loader;
    response["policy_seq"] = policy_loader.policy_seq(policy);
    LockGuard guard;
    response["lock_digest"] = guard.lock_digest(policy);

    const Json::Value& rows = request["rows"];
    BatchGate gate;
    GateResult gate_result = gate.screen(rows, policy);
    if (!gate_result.allowed) {
        response["accepted"] = 0;
        response["rejected"] = static_cast<int>(rows.size());
        Json::Value scores(Json::arrayValue);
        for (const auto& row : rows) {
            Json::Value entry(Json::objectValue);
            entry["row_id"] = row["row_id"];
            entry["score"] = Json::Value::null;
            entry["feature_digest"] = Json::Value::null;
            entry["status"] = "rejected";
            scores.append(entry);
        }
        response["scores"] = scores;
        return response;
    }

    if (!guard.probe("/app/environment/sidecar/poetry.lock", policy)) {
        response["accepted"] = 0;
        response["rejected"] = static_cast<int>(rows.size());
        Json::Value scores(Json::arrayValue);
        for (const auto& row : rows) {
            Json::Value entry(Json::objectValue);
            entry["row_id"] = row["row_id"];
            entry["score"] = Json::Value::null;
            entry["feature_digest"] = Json::Value::null;
            entry["status"] = "rejected";
            scores.append(entry);
        }
        response["scores"] = scores;
        return response;
    }

    SidecarExec sidecar;
    Json::Value features;
    if (!sidecar.launch(rows, policy, features)) {
        response["accepted"] = 0;
        response["rejected"] = static_cast<int>(rows.size());
        Json::Value scores(Json::arrayValue);
        for (const auto& row : rows) {
            Json::Value entry(Json::objectValue);
            entry["row_id"] = row["row_id"];
            entry["score"] = Json::Value::null;
            entry["feature_digest"] = Json::Value::null;
            entry["status"] = "rejected";
            scores.append(entry);
        }
        response["scores"] = scores;
        return response;
    }

    RowScorer scorer;
    Json::Value scores(Json::arrayValue);
    int accepted = 0;
    int rejected = 0;
    for (const auto& row : rows) {
        std::string row_id = row["row_id"].asString();
        Json::Value entry(Json::objectValue);
        entry["row_id"] = row_id;
        if (!features.isMember(row_id)) {
            entry["score"] = Json::Value::null;
            entry["feature_digest"] = Json::Value::null;
            entry["status"] = "rejected";
            rejected += 1;
        } else {
            const Json::Value& feat = features[row_id];
            double raw = scorer.blend(feat, weights, policy);
            double factor = std::pow(10.0, policy.score_precision);
            double rounded = std::round(raw * factor) / factor;
            entry["score"] = rounded;
            entry["feature_digest"] = scorer.feature_digest(feat);
            entry["status"] = "ok";
            accepted += 1;
        }
        scores.append(entry);
    }
    response["accepted"] = accepted;
    response["rejected"] = rejected;
    Json::Value ordered(Json::arrayValue);
    std::vector<Json::Value> rows_out;
    for (const auto& entry : scores) {
        rows_out.push_back(entry);
    }
    std::sort(rows_out.begin(), rows_out.end(),
              [](const Json::Value& a, const Json::Value& b) {
                  return a["row_id"].asString() < b["row_id"].asString();
              });
    for (const auto& entry : rows_out) {
        ordered.append(entry);
    }
    response["scores"] = ordered;
    return response;
}
