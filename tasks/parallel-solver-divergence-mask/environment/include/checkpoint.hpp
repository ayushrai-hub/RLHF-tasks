#pragma once
#include "types.hpp"
#include <string>
Checkpoint load_checkpoint(const std::string& path);
void save_checkpoint(const std::string& path, const Checkpoint& cp);