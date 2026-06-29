#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace p7 {
std::string sha256_hex(const std::string& data);
uint32_t crc32_line(uint32_t seq, const std::string& opcode, uint32_t scenario);
std::string read_file(const std::string& path);
void write_file(const std::string& path, const std::string& data);
}  // namespace p7
