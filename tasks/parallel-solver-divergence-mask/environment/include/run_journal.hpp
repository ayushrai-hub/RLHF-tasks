#pragma once

#include <cstdint>
#include <string>

struct JournalTail {
    int seed;
    int workers;
    int phase_id;
    double dispersion_snapshot;
    std::string fold_token;
    uint64_t audit_link;
    bool present;
};

JournalTail read_journal_tail(const std::string& path);
int resolve_phase_id(const std::string& path, const std::string& mode);
void append_journal_entry(
    const std::string& path,
    int seed,
    int workers,
    int phase_id,
    double dispersion,
    const std::string& fold_token,
    uint64_t audit_link);
void validate_journal_continuation(const JournalTail& tail, int seed, int workers);
