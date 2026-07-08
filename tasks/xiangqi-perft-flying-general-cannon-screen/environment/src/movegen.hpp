#pragma once
#include "board.hpp"
#include <vector>

struct Move {
    int from, to;
};

void apply_move(State &s, const Move &m);
void legal_moves(const State &s, std::vector<Move> &out);
