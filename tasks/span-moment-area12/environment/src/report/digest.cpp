#include "model/beam.hpp"

#include "seal/sha256.hpp"

#include <iomanip>
#include <sstream>

namespace beam::report {

namespace {

std::string json_number(double value) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(6) << value;
    std::string s = out.str();
    while (s.size() > 1 && s.back() == '0' && s.find('.') != std::string::npos) {
        s.pop_back();
    }
    if (!s.empty() && s.back() == '.') {
        s.pop_back();
    }
    return s;
}

}  // namespace

std::string compute_report_digest(const EnvelopeReport& report) {
    std::ostringstream payload;
    payload << report.beam_id << "|" << report.combination << "|"
            << report.provenance.committed_revision << "|"
            << report.provenance.amendment_generation << "|"
            << json_number(report.envelope.max_moment_nm) << "|"
            << json_number(report.envelope.max_deflection_mm);
    return "sha256:" + sha256_hex(payload.str());
}

}  // namespace beam::report
