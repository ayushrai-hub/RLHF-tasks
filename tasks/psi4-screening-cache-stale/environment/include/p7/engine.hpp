#pragma once
#include "p7/epoch_row.hpp"
#include <cstdint>
#include <string>
#include <vector>
namespace p7 {
std::vector<EpochRow> run_scenario(uint32_t scenario_id, bool cold);
void run_chain(uint32_t from_id, uint32_t to_id, bool cold);
void replay_all(bool cold);
void recover_from_wal();
std::string inspect_cross();
std::string emit_out(const std::string& path);
}
