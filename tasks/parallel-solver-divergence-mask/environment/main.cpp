#include "engine.hpp"
#include "loader.hpp"

#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
std::string require_value(int& i, int argc, char** argv) {
    if (i + 1 >= argc) {
        throw std::runtime_error("missing value for flag");
    }
    ++i;
    return argv[i];
}
}  // namespace

int main(int argc, char** argv) {
    try {
        RunArgs args{};
        args.out_dir = "/app/output";
        args.workers = 2;
        args.seed = 7;
        args.mode = "fresh";

        for (int i = 1; i < argc; ++i) {
            const std::string f = argv[i];
            if (f == "--out") {
                args.out_dir = require_value(i, argc, argv);
            } else if (f == "--workers") {
                args.workers = std::stoi(require_value(i, argc, argv));
            } else if (f == "--seed") {
                args.seed = std::stoi(require_value(i, argc, argv));
            } else if (f == "--mode") {
                args.mode = require_value(i, argc, argv);
            } else if (f == "--save") {
                args.save_path = require_value(i, argc, argv);
            } else if (f == "--load") {
                args.load_path = require_value(i, argc, argv);
            } else if (f == "--layout") {
                args.layout = require_value(i, argc, argv);
            } else if (f == "--journal") {
                args.journal_path = require_value(i, argc, argv);
            } else {
                throw std::runtime_error("unknown flag: " + f);
            }
        }

        const auto rows = load_cases("/app/data/cases.csv");
        return run_engine(args, rows);
    } catch (const std::exception& ex) {
        std::cerr << ex.what() << "\n";
        return 1;
    }
}
