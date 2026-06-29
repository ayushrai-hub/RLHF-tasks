#pragma once
#include "p7/epoch_row.hpp"
#include <cstdint>
#include <string>
#include <vector>
int WIDE_ON_CACHED();
int compare_t4(double stored, double target, bool cached);
std::string epoch_fp(const std::vector<p7::EpochRow>& epochs);
bool rms_band_ok(double rms);
