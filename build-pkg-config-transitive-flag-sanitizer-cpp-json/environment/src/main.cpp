#include "audit.hpp"
#include "cli.hpp"
#include "json_writer.hpp"
#include "manifest.hpp"
#include "pc_parser.hpp"
#include "resolver.hpp"

#include <fstream>
#include <iostream>

int main(int argc, char** argv) {
    try {
        Options opt = parse_args(argc, argv);
        Manifest manifest = read_manifest(opt.manifest);
        auto packages = parse_pc_directory(opt.pc_dir);
        std::ofstream out(opt.out);
        if (!out) throw std::runtime_error("cannot open output");
        if (opt.command == "parse") write_parse_json(out, packages);
        else if (opt.command == "resolve") write_resolve_json(out, resolve_roots(packages, manifest));
        else if (opt.command == "audit") write_audit_json(out, audit_packages(packages, manifest));
        else throw std::runtime_error("unknown command " + opt.command);
    } catch (const std::exception& ex) {
        std::cerr << "pc-sanitize: " << ex.what() << "\n";
        return 2;
    }
    return 0;
}
