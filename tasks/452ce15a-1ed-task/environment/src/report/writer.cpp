#include "model/beam.hpp"

#include <fstream>
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

std::string compute_report_digest(const EnvelopeReport& report);

void write_report(const EnvelopeReport& report, const std::string& path) {
    EnvelopeReport copy = report;
    copy.report_digest = compute_report_digest(copy);

    std::ofstream out(path);
    out << std::fixed << std::setprecision(6);
    out << "{\n";
    out << "  \"schema_version\": " << copy.schema_version << ",\n";
    out << "  \"beam_id\": \"" << copy.beam_id << "\",\n";
    out << "  \"combination\": \"" << copy.combination << "\",\n";
    out << "  \"provenance\": {\n";
    out << "    \"committed_revision\": " << copy.provenance.committed_revision << ",\n";
    out << "    \"amendment_generation\": " << copy.provenance.amendment_generation << ",\n";
    out << "    \"accepted_stages\": " << copy.provenance.accepted_stages << ",\n";
    out << "    \"rejected_stages\": " << copy.provenance.rejected_stages << "\n";
    out << "  },\n";
    out << "  \"envelope\": {\n";
    out << "    \"left_reaction_n\": " << json_number(copy.envelope.left_reaction_n) << ",\n";
    out << "    \"right_reaction_n\": " << json_number(copy.envelope.right_reaction_n) << ",\n";
    out << "    \"max_moment_nm\": " << json_number(copy.envelope.max_moment_nm) << ",\n";
    out << "    \"min_moment_nm\": " << json_number(copy.envelope.min_moment_nm) << ",\n";
    out << "    \"max_shear_n\": " << json_number(copy.envelope.max_shear_n) << ",\n";
    out << "    \"min_shear_n\": " << json_number(copy.envelope.min_shear_n) << ",\n";
    out << "    \"max_deflection_mm\": " << json_number(copy.envelope.max_deflection_mm) << ",\n";
    out << "    \"min_deflection_mm\": " << json_number(copy.envelope.min_deflection_mm) << "\n";
    out << "  },\n";
    out << "  \"report_digest\": \"" << copy.report_digest << "\"\n";
    out << "}\n";
}

}  // namespace beam::report
