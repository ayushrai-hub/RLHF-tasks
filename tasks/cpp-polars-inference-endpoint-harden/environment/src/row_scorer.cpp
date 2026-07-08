#include "score/row_scorer.hpp"

#include <algorithm>
#include <cmath>
#include <iomanip>
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

double RowScorer::blend(const Json::Value& features, const Json::Value& weights,
                        const Policy& policy) {
    (void)policy;
    double total = weights.get("bias", 0.0).asDouble();
    for (const auto& key : features.getMemberNames()) {
        if (weights.isMember(key)) {
            total += features[key].asDouble() * weights[key].asDouble();
        }
    }
    return total;
}

std::string RowScorer::feature_digest(const Json::Value& features) const {
    std::vector<Json::String> keys = features.getMemberNames();
    std::sort(keys.begin(), keys.end());
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(6);
    oss << "{";
    for (size_t i = 0; i < keys.size(); ++i) {
        if (i > 0) {
            oss << ",";
        }
        oss << "\"" << keys[i] << "\":" << features[keys[i]].asDouble();
    }
    oss << "}";
    return sha256_hex(oss.str()).substr(0, 16);
}
