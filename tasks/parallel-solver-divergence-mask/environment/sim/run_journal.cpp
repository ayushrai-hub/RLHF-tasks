#include "run_journal.hpp"

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace {

JournalTail empty_tail() {
    JournalTail t{};
    t.present = false;
    return t;
}

std::vector<std::string> read_data_lines(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        return {};
    }
    std::vector<std::string> lines;
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty() || line[0] == '#') {
            continue;
        }
        lines.push_back(line);
    }
    return lines;
}

JournalTail read_journal_tail_impl(const std::string& path) {
    const auto lines = read_data_lines(path);
    if (lines.empty()) {
        return empty_tail();
    }
    JournalTail tail{};
    std::istringstream iss(lines.back());
    iss >> tail.seed >> tail.workers >> tail.phase_id >> tail.dispersion_snapshot >> tail.fold_token >>
        tail.audit_link;
    if (!iss) {
        throw std::runtime_error("journal tail malformed");
    }
    tail.present = true;
    return tail;
}

}  // namespace

JournalTail read_journal_tail(const std::string& path) {
    return read_journal_tail_impl(path);
}

int resolve_phase_id(const std::string& path, const std::string& mode) {
    const auto tail = read_journal_tail_impl(path);
    if (mode == "fresh" || !tail.present) {
        return 0;
    }
    return tail.phase_id;
}

void append_journal_entry(
    const std::string& path,
    int seed,
    int workers,
    int phase_id,
    double dispersion,
    const std::string& fold_token,
    uint64_t audit_link) {
    std::ofstream out(path, std::ios::app);
    if (!out) {
        throw std::runtime_error("cannot append journal");
    }
    out << seed << ' ' << workers << ' ' << phase_id << ' ' << dispersion << ' ' << fold_token << ' ' << audit_link
        << '\n';
}

void validate_journal_continuation(const JournalTail& tail, int seed, int workers) {
    if (!tail.present) {
        throw std::runtime_error("journal missing for continued run");
    }
    if (tail.seed != seed || tail.workers != workers) {
        throw std::runtime_error("journal tail mismatch");
    }
}
