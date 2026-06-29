#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace p7 {
struct WalLine {
  uint32_t seq{0};
  std::string opcode;
  uint32_t scenario{0};
  uint32_t crc{0};
};
constexpr uint32_t SEAL_MAGIC = 0xBEEF;
std::vector<WalLine> read_wal();
uint32_t append_wal(const std::string& opcode, uint32_t scenario);
uint32_t recompute_seal();
uint32_t compute_seal();
uint32_t read_seal();
bool validate_wal();
bool seal_matches();
bool bust_before_ok();
bool seq_monotone();
void reset_wal();
}  // namespace p7
