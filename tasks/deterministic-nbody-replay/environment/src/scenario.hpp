#pragma once
#include "body.hpp"
#include <cstdint>
#include <string>
#include <vector>

struct ScenarioParams {
    double dt;
    double softening2;
    double G;
    uint64_t seed;
    int32_t body_count;
    uint8_t version;
    uint8_t dim;

    // Three-body activation (body_index == -1 means no activation)
    int32_t activation_body_index = -1;
    uint64_t activation_step = 0;
};

// Read an .icbin scenario file.  Populates bodies and params.
// Returns true on success, false on format error.
bool load_scenario(const std::string& path,
                   std::vector<Body>& bodies,
                   ScenarioParams& params);
