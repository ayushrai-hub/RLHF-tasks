#pragma once
#include "piece.hpp"

struct State {
    int b[90];
    int side;
};

static inline int idx(int r, int f) { return r * 9 + f; }
static inline bool onb(int r, int f) { return r >= 0 && r < 10 && f >= 0 && f < 9; }
static inline int fwd(int color) { return color == 0 ? -1 : 1; }

static inline bool in_palace(int color, int r, int f) {
    if (f < 3 || f > 5) return false;
    return color == 0 ? (r >= 7 && r <= 9) : (r >= 0 && r <= 2);
}

static inline bool own_half(int color, int r) {
    return color == 0 ? (r >= 5) : (r <= 4);
}

static inline bool crossed_river(int color, int r) {
    return color == 0 ? (r <= 4) : (r >= 5);
}
