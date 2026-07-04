#pragma once
#include <cstdint>

struct Body {
    double mass;

    // Position (canonical state)
    double x, y, z;

    // Integer-step velocity
    double vx, vy, vz;

    // Half-step velocity carry (leapfrog KDK internal state).
    double vhx, vhy, vhz;

    // Kahan compensation terms for position accumulation.
    double kc_x, kc_y, kc_z;

    // Current acceleration — computed each step, not saved in checkpoint.
    double ax, ay, az;

    // Canonical body index from the scenario file (0-based, order of appearance).
    // Used as the primary sort key for force reduction ordering.
    int32_t canonical_index;

    // Whether this body is currently active (contributes pairwise forces).
    // Inactive bodies are frozen in place and exert/receive no force.
    bool active;

    // Padding to reach natural alignment for the struct array.
    char _pad[3];
};
