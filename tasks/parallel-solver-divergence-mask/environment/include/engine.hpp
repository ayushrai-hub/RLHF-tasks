#pragma once
#include "types.hpp"
#include <string>
#include <vector>
struct RunArgs {
    std::string out_dir;
    int workers;
    int seed;
    std::string mode;
    std::string save_path;
    std::string load_path;
    std::string layout;
    std::string journal_path;
};
int run_engine(const RunArgs& args, const std::vector<CaseRow>& rows);
