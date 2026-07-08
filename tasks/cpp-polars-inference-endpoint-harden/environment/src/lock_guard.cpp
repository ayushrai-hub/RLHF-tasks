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
    (void)lock_path;
    (void)policy;
    return true;
}

std::string LockGuard::lock_digest(const Policy& policy) const {
    std::string payload = "polars==" + policy.polars_pin;
    return sha256_hex(payload).substr(0, 16);
}
