#pragma once

#include "models.hpp"

#include <map>
#include <string>

std::map<std::string, Package> parse_pc_directory(const std::string& dir);
