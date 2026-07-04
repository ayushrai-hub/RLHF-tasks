#ifndef GLYPHVAULT_MOVE_DRIVER_H
#define GLYPHVAULT_MOVE_DRIVER_H

#include "glyphvault/types.h"

int gv_load_moves(const char *path, char moves[][GV_MAX_LINE], int max_moves);
int gv_apply_move(gv_state *st, const char *move_text);

#endif
