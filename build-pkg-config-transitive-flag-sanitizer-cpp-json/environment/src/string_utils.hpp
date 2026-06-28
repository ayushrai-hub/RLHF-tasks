#pragma once

#include <string>
#include <vector>

std::string trim(const std::string& value);
std::vector<std::string> split_ws(const std::string& value);
std::vector<std::string> split_requires(const std::string& value);
std::string package_name_from_requirement(const std::string& value);
