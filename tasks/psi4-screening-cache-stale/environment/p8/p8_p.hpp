#pragma once
#include <cstdint>
#include <string>
#include <vector>
int SKIP_JOURNAL_BUST();
std::vector<std::string> step_p8(uint32_t scenario_id, const std::vector<std::string>& roots);
