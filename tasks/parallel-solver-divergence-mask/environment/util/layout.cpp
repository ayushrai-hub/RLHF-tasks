#include "layout.hpp"

#include <fstream>
#include <string>

int layout_span(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        return 0;
    }
    int lines = 0;
    std::string row;
    while (std::getline(in, row)) {
        if (!row.empty()) {
            ++lines;
        }
    }
    return lines;
}