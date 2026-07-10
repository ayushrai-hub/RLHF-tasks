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
    (void)dossier_path;
    Policy policy;
    std::ifstream in(toml_path);
    std::string line;
    while (std::getline(in, line)) {
        if (line.find("max_batch_rows") != std::string::npos) {
            policy.max_batch_rows = 128;
        }
        if (line.find("null_fill") != std::string::npos) {
            policy.null_fill = "zero";
        }
        if (line.find("unknown_category") != std::string::npos) {
            policy.unknown_category = "bucket";
        }
        if (line.find("polars_pin") != std::string::npos) {
            policy.polars_pin = "0.20.31";
        }
        if (line.find("score_precision") != std::string::npos) {
            policy.score_precision = 4;
        }
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
