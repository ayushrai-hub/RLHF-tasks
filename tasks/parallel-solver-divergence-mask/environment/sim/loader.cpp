#include "loader.hpp"

#include <fstream>
#include <sstream>
#include <stdexcept>

std::vector<CaseRow> load_cases(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        throw std::runtime_error("unable to open case data");
    }
    std::vector<CaseRow> out;
    std::string line;
    bool first = true;
    while (std::getline(in, line)) {
        if (line.empty()) {
            continue;
        }
        if (first) {
            first = false;
            continue;
        }
        std::stringstream ss(line);
        std::string id;
        std::string bias_s;
        std::string slope_s;
        if (!std::getline(ss, id, ',')) {
            continue;
        }
        std::getline(ss, bias_s, ',');
        std::getline(ss, slope_s, ',');
        CaseRow row{};
        row.id = id;
        row.bias = std::stod(bias_s);
        row.slope = std::stod(slope_s);
        out.push_back(row);
    }
    if (out.empty()) {
        throw std::runtime_error("case data is empty");
    }
    return out;
}