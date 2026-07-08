#pragma once

#include "model/beam.hpp"

#include <string>

namespace beam::report {

void write_report(const EnvelopeReport& report, const std::string& path);

}  // namespace beam::report
