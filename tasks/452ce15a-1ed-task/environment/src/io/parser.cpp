#include "io/parser.hpp"
#include "io/diagnostic.hpp"

#include <fstream>
#include <sstream>

namespace beam::io {

std::string trim(const std::string& line) {
    std::size_t start = 0;
    while (start < line.size() && std::isspace(static_cast<unsigned char>(line[start]))) {
        ++start;
    }
    std::size_t end = line.size();
    while (end > start && std::isspace(static_cast<unsigned char>(line[end - 1]))) {
        --end;
    }
    return line.substr(start, end - start);
}

double parse_key_double(const std::string& line, const std::string& key) {
    const std::string prefix = key + "=";
    if (line.rfind(prefix, 0) != 0) {
        return 0.0;
    }
    return std::stod(trim(line.substr(prefix.size())));
}

double parse_key_double_anywhere(const std::string& line, const std::string& key) {
    const std::string token = key + "=";
    const auto pos = line.find(token);
    if (pos == std::string::npos) {
        return 0.0;
    }
    std::size_t start = pos + token.size();
    std::size_t end = start;
    while (end < line.size() && !std::isspace(static_cast<unsigned char>(line[end]))) {
        ++end;
    }
    return std::stod(trim(line.substr(start, end - start)));
}

}  // namespace

namespace beam::io {

ParsedStage parse_stage_file(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        throw ParseError("cannot open beam stage: " + path);
    }

    ParsedStage stage;
    LoadCase* current_case = nullptr;
    std::string section;
    std::string line;

    while (std::getline(in, line)) {
        const std::string trimmed = trim(line);
        if (trimmed.empty() || trimmed[0] == '#') {
            continue;
        }
        if (trimmed.rfind("beam_id=", 0) == 0) {
            stage.model.beam_id = trim(trimmed.substr(8));
            continue;
        }
        if (trimmed.rfind("revision=", 0) == 0) {
            stage.model.revision = static_cast<int>(std::stoi(trim(trimmed.substr(9))));
            continue;
        }
        if (trimmed.rfind("amendment=", 0) == 0) {
            stage.directive.is_amendment = true;
            const std::string value = trim(trimmed.substr(10));
            stage.directive.accept = (value == "accept");
            continue;
        }
        if (trimmed.rfind("integrity=", 0) == 0) {
            stage.directive.integrity = trim(trimmed.substr(10));
            continue;
        }
        if (trimmed == "nodes:") {
            section = "nodes";
            continue;
        }
        if (trimmed == "segments:") {
            section = "segments";
            continue;
        }
        if (trimmed == "stiffness:") {
            section = "stiffness";
            continue;
        }
        if (trimmed == "load_cases:") {
            section = "load_cases";
            current_case = nullptr;
            continue;
        }
        if (trimmed == "combinations:") {
            section = "combinations";
            current_case = nullptr;
            continue;
        }
        if (section == "load_cases" && trimmed.rfind("POINT") != 0 && trimmed.rfind("UDL") != 0 &&
            trimmed.rfind("replace_") != 0) {
            LoadCase lc;
            lc.name = trimmed;
            stage.model.load_cases.push_back(lc);
            current_case = &stage.model.load_cases.back();
            continue;
        }

        if (trimmed.rfind("replace_segment ", 0) == 0) {
            stage.directive.replace_segments.push_back(trimmed);
            continue;
        }
        if (trimmed.rfind("replace_load_case ", 0) == 0) {
            stage.directive.replace_load_cases.push_back(trimmed);
            const std::string name = trim(trimmed.substr(18));
            LoadCase lc;
            lc.name = name;
            stage.model.load_cases.push_back(lc);
            current_case = &stage.model.load_cases.back();
            continue;
        }

        if (section == "nodes") {
            std::istringstream row(trimmed);
            double x = 0.0;
            std::string support;
            row >> x >> support;
            Node node;
            node.x_m = x;
            node.support = (support == "ROLLER") ? SupportType::ROLLER : SupportType::PIN;
            if (trimmed.find("settlement_mm=") != std::string::npos) {
                node.settlement_mm = parse_key_double(trimmed, "settlement_mm");
            }
            stage.model.nodes.push_back(node);
        } else if (section == "segments") {
            std::istringstream row(trimmed);
            Segment seg;
            row >> seg.id >> seg.x0_m >> seg.x1_m;
            if (trimmed.find("E_gpa=") != std::string::npos) {
                seg.E_pa = parse_key_double_anywhere(trimmed, "E_gpa") * 1e9;
            } else if (trimmed.find("E_pa=") != std::string::npos) {
                seg.E_pa = parse_key_double_anywhere(trimmed, "E_pa");
            }
            if (trimmed.find("I_m4=") != std::string::npos) {
                seg.I_m4 = parse_key_double_anywhere(trimmed, "I_m4");
            }
            seg.width_mm = parse_key_double_anywhere(trimmed, "section_width_mm");
            seg.depth_mm = parse_key_double_anywhere(trimmed, "section_depth_mm");
            if (seg.I_m4 <= 0.0 && seg.width_mm > 0.0 && seg.depth_mm > 0.0) {
                const double b = seg.width_mm / 1000.0;
                const double h = seg.depth_mm / 1000.0;
                seg.I_m4 = b * h * h * h / 12.0;
            }
            stage.model.segments.push_back(seg);
        } else if (section == "stiffness") {
            std::istringstream row(trimmed);
            StiffnessRegion region;
            std::string label;
            row >> label >> region.segment_id >> region.x0_m >> region.x1_m;
            region.factor = parse_key_double_anywhere(trimmed, "factor");
            if (region.factor <= 0.0) {
                region.factor = 1.0;
            }
            stage.model.stiffness.push_back(region);
        } else if (section == "combinations") {
            std::istringstream row(trimmed);
            Combination combo;
            row >> combo.name;
            std::string token;
            while (row >> token) {
                const auto colon = token.find(':');
                if (colon == std::string::npos) {
                    throw ParseError("invalid combination term in " + path);
                }
                CombinationTerm term;
                term.case_name = token.substr(0, colon);
                term.factor = std::stod(token.substr(colon + 1));
                combo.terms.push_back(term);
            }
            bool merged = false;
            for (auto& existing : stage.model.combinations) {
                if (existing.name == combo.name) {
                    existing.terms.insert(existing.terms.end(), combo.terms.begin(), combo.terms.end());
                    merged = true;
                    break;
                }
            }
            if (!merged) {
                stage.model.combinations.push_back(combo);
            }
        } else if (current_case != nullptr) {
            std::istringstream row(trimmed);
            std::string kind;
            row >> kind;
            if (kind == "POINT_F") {
                PointForce pf;
                row >> pf.force_n >> pf.x_m;
                current_case->point_forces.push_back(pf);
            } else if (kind == "POINT_M") {
                PointMoment pm;
                row >> pm.moment_nm >> pm.x_m;
                current_case->point_moments.push_back(pm);
            } else if (kind == "UDL") {
                UdlLoad udl;
                row >> udl.w_n_per_m >> udl.x0_m >> udl.x1_m;
                current_case->udls.push_back(udl);
            } else {
                throw ParseError("unknown load row in " + path);
            }
        }
    }

    if (stage.model.beam_id.empty()) {
        throw ParseError("beam_id required in " + path);
    }
    return stage;
}

}  // namespace beam::io
