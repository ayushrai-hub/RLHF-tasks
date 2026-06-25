#pragma once

#include <cstdint>
#include <string>

uint64_t compute_audit_link(
    int seed,
    const std::string& fold_token,
    double objective);

std::string audit_link_hex(uint64_t link);
