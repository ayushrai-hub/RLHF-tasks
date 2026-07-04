#pragma once
#include "body.hpp"
#include "scenario.hpp"
#include <cstdint>
#include <cstdio>
#include <vector>

// Run the KDK leapfrog integrator from the current body state for num_steps steps.
// Writes one trajectory record per step to traj_out (may be nullptr to skip).
// If chk_out is not nullptr, writes a checkpoint at chk_step and closes the file.
// Returns true on success.
bool run_integration(std::vector<Body>& bodies,
                     const ScenarioParams& params,
                     uint64_t start_step,
                     uint64_t num_steps,
                     FILE* traj_out,
                     FILE* chk_out,
                     uint64_t chk_step);

// Initialise the half-step velocity carry from the initial body state.
// Must be called once after loading initial conditions and before the first step.
void init_half_step(std::vector<Body>& bodies, const ScenarioParams& params);
