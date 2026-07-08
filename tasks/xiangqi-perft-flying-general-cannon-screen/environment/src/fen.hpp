#pragma once
#include "board.hpp"
#include <string>

bool parse_fen(const std::string &placement, const std::string &side, State &s);
