#pragma once

#include <cstdint>
#include <string>

class Sha256 {
  public:
    Sha256();
    void update(const std::uint8_t* data, std::size_t len);
    void update(const std::string& data);
    std::string hex_digest() const;

  private:
    void transform(const std::uint8_t block[64]);
    void pad();

    std::uint32_t state_[8];
    std::uint64_t bitlen_;
    std::uint8_t buffer_[64];
    std::size_t buffer_len_;
};

std::string sha256_hex(const std::string& data);
