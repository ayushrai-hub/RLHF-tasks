#pragma once

enum { EMPTY = 0, GENERAL = 1, ADVISOR = 2, ELEPHANT = 3, HORSE = 4, CHARIOT = 5, CANNON = 6, SOLDIER = 7 };

static inline int enc(int color, int type) { return (color << 3) | type; }
static inline int col_of(int p) { return (p >> 3) & 1; }
static inline int type_of(int p) { return p & 7; }
