#pragma once
#include "p7/epoch_row.hpp"
#include <string>
#include <vector>
std::string digest_for_epochs(const std::vector<p7::EpochRow>& epochs);
void emit_trace(const std::string& out, const std::vector<p7::EpochRow>& epochs);
