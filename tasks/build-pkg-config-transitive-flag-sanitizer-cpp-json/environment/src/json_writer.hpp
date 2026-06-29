#pragma once

#include "models.hpp"

#include <map>
#include <ostream>

void write_parse_json(std::ostream& out, const std::map<std::string, Package>& packages);
void write_resolve_json(std::ostream& out, const std::vector<RootResolution>& roots);
void write_audit_json(std::ostream& out, const std::vector<Finding>& findings);
