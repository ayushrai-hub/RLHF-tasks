#pragma once

#include "models.hpp"

#include <map>
#include <vector>

std::vector<Finding> audit_packages(const std::map<std::string, Package>& packages, const Manifest& manifest);
