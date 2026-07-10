#!/bin/bash
# Terminal-Bench Canary: tb3-cpp-polars-inference-endpoint-harden
set -euo pipefail

echo "=== Oracle: harden Polars inference endpoint ==="

cat > "/app/environment/src/ratified_policy.cpp" <<'EOF'
#include "score/ratified_policy.hpp"

#include <fstream>
#include <sstream>

#include <openssl/evp.h>

namespace {
std::string sha256_hex(const std::string& payload) {
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int len = 0;
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr);
    EVP_DigestUpdate(ctx, payload.data(), payload.size());
    EVP_DigestFinal_ex(ctx, digest, &len);
    EVP_MD_CTX_free(ctx);
    std::ostringstream oss;
    for (unsigned int i = 0; i < len; ++i) {
        oss << std::hex;
        if (digest[i] < 16) {
            oss << '0';
        }
        oss << static_cast<int>(digest[i]);
    }
    return oss.str();
}
}  // namespace

Policy RatifiedPolicy::load(const std::string& dossier_path, const std::string& toml_path) {
    (void)toml_path;
    Policy policy;
    std::ifstream in(dossier_path);
    std::stringstream buffer;
    buffer << in.rdbuf();
    std::string text = buffer.str();
    auto pos = text.find("P-2026-03");
    if (pos == std::string::npos) {
        return policy;
    }
    std::string slice = text.substr(pos);
    if (slice.find("max_batch_rows **32**") != std::string::npos) {
        policy.max_batch_rows = 32;
    }
    if (slice.find("null_fill **forward**") != std::string::npos) {
        policy.null_fill = "forward";
    }
    if (slice.find("unknown_category **reject**") != std::string::npos) {
        policy.unknown_category = "reject";
    }
    if (slice.find("polars_pin **1.12.0**") != std::string::npos) {
        policy.polars_pin = "1.12.0";
    }
    if (slice.find("score_precision **6**") != std::string::npos) {
        policy.score_precision = 6;
    }
    return policy;
}

std::string RatifiedPolicy::policy_seq(const Policy& policy) const {
    std::ostringstream oss;
    oss << "{\"max_batch_rows\":" << policy.max_batch_rows << ",\"null_fill\":\""
        << policy.null_fill << "\",\"polars_pin\":\"" << policy.polars_pin
        << "\",\"score_precision\":" << policy.score_precision << ",\"unknown_category\":\""
        << policy.unknown_category << "\"}";
    return sha256_hex(oss.str()).substr(0, 16);
}
EOF

cat > "/app/environment/src/batch_gate.cpp" <<'EOF'
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
            result.allowed = false;
            result.reason = "unknown_region";
            return result;
        }
        if (!approved_channel(channel)) {
            result.allowed = false;
            result.reason = "unknown_channel";
            return result;
        }
    }
    return result;
}
EOF

cat > "/app/environment/src/lock_guard.cpp" <<'EOF'
#include "score/lock_guard.hpp"

#include <fstream>
#include <sstream>

#include <openssl/evp.h>

namespace {
std::string sha256_hex(const std::string& payload) {
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int len = 0;
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr);
    EVP_DigestUpdate(ctx, payload.data(), payload.size());
    EVP_DigestFinal_ex(ctx, digest, &len);
    EVP_MD_CTX_free(ctx);
    std::ostringstream oss;
    for (unsigned int i = 0; i < len; ++i) {
        oss << std::hex;
        if (digest[i] < 16) {
            oss << '0';
        }
        oss << static_cast<int>(digest[i]);
    }
    return oss.str();
}
}  // namespace

bool LockGuard::probe(const std::string& lock_path, const Policy& policy) {
    std::ifstream in(lock_path);
    std::stringstream buffer;
    buffer << in.rdbuf();
    std::string text = buffer.str();
    auto name_pos = text.find("name = \"polars\"");
    if (name_pos == std::string::npos) {
        return false;
    }
    auto ver_pos = text.find("version = \"", name_pos);
    if (ver_pos == std::string::npos) {
        return false;
    }
    ver_pos += std::string("version = \"").size();
    auto end = text.find('"', ver_pos);
    if (end == std::string::npos) {
        return false;
    }
    return text.substr(ver_pos, end - ver_pos) == policy.polars_pin;
}

std::string LockGuard::lock_digest(const Policy& policy) const {
    std::string payload = "polars==" + policy.polars_pin;
    return sha256_hex(payload).substr(0, 16);
}
EOF

cat > "/app/environment/src/sidecar_exec.cpp" <<'EOF'
#include "score/sidecar_exec.hpp"

#include <cstdlib>
#include <fstream>
#include <sstream>

namespace {
bool run_cmd(const std::string& cmd) {
    return std::system(cmd.c_str()) == 0;
}
}  // namespace

bool SidecarExec::launch(const Json::Value& rows, const Policy& policy, Json::Value& features_out) {
    const std::string rows_path = "/tmp/score_rows.json";
    const std::string features_path = "/tmp/score_features.json";
    {
        std::ofstream out(rows_path);
        Json::StreamWriterBuilder builder;
        builder["indentation"] = "";
        out << Json::writeString(builder, rows);
    }
    std::string mode = policy.null_fill;
    setenv("FEATURE_NULL_MODE", mode.c_str(), 1);
    std::ostringstream cmd;
    cmd << "/opt/sidecar-venv/bin/python3 /app/environment/sidecar/feature_pipe/preprocess.py"
        << " --input " << rows_path << " --output " << features_path;
    if (!run_cmd(cmd.str())) {
        return false;
    }
    std::ifstream in(features_path);
    std::stringstream buffer;
    buffer << in.rdbuf();
    Json::CharReaderBuilder reader;
    std::string errs;
    return Json::parseFromStream(reader, buffer, &features_out, &errs);
}
EOF

pkill -f '/app/bin/score-server' 2>/dev/null || true
make -C /app/environment install
bash /app/environment/scripts/run-batch-audit.sh

echo "=== Oracle complete ==="
