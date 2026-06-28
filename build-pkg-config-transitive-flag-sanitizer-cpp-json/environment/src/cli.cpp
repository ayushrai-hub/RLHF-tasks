#include "cli.hpp"

#include <stdexcept>

Options parse_args(int argc, char** argv) {
    if (argc < 2) throw std::runtime_error("missing command");
    Options opt;
    opt.command = argv[1];
    for (int i = 2; i < argc; ++i) {
        std::string key = argv[i];
        if (i + 1 >= argc) throw std::runtime_error("missing value for " + key);
        std::string value = argv[++i];
        if (key == "--pc-dir") opt.pc_dir = value;
        else if (key == "--manifest") opt.manifest = value;
        else if (key == "--out") opt.out = value;
        else throw std::runtime_error("unknown option " + key);
    }
    if (opt.pc_dir.empty() || opt.manifest.empty() || opt.out.empty()) {
        throw std::runtime_error("required flags: --pc-dir, --manifest, --out");
    }
    return opt;
}
