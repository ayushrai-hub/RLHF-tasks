#include "checkpoint.hpp"

#include <fstream>
#include <stdexcept>

Checkpoint load_checkpoint(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        throw std::runtime_error("checkpoint missing");
    }
    Checkpoint cp{};
    in >> cp.seed;
    in >> cp.workers;
    in >> cp.saved_dispersion;
    if (!in) {
        throw std::runtime_error("checkpoint malformed");
    }
    return cp;
}

void save_checkpoint(const std::string& path, const Checkpoint& cp) {
    std::ofstream out(path);
    if (!out) {
        throw std::runtime_error("cannot write checkpoint");
    }
    out << cp.seed << "\n";
    out << cp.workers << "\n";
    out << cp.saved_dispersion << "\n";
}