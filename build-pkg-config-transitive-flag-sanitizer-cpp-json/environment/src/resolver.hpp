#pragma once

#include "models.hpp"

#include <map>
#include <vector>

std::vector<RootResolution> resolve_roots(const std::map<std::string, Package>& packages, const Manifest& manifest);
