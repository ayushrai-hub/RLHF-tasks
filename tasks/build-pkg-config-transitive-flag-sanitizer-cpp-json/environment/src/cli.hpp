#pragma once

#include <map>
#include <string>

struct Options {
    std::string command;
    std::string pc_dir;
    std::string manifest;
    std::string out;
};

Options parse_args(int argc, char** argv);
