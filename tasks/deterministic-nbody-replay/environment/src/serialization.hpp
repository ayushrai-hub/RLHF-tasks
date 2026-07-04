#pragma once
#include "body.hpp"
#include "scenario.hpp"
#include <cstdint>
#include <cstdio>
#include <vector>

// Write a checkpoint to an open file at the given step.
// Returns true on success.
bool write_checkpoint(FILE* f, const std::vector<Body>& bodies, uint64_t step);

// Read a checkpoint file and populate bodies and step.
// Returns true on success.
bool read_checkpoint(const std::string& path,
                     std::vector<Body>& bodies,
                     uint64_t& step_out);
