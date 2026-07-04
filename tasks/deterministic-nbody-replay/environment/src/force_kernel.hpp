#pragma once
#include "body.hpp"
#include <vector>

// Compute pairwise gravitational accelerations for all active bodies.
// All bodies are sorted before accumulation; the sort key and ordering
// affect the floating-point results (non-associativity).
void compute_forces(std::vector<Body>& bodies, double G, double softening2);
