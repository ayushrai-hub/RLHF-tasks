#ifndef GLYPHVAULT_ROOM_ENGINE_H
#define GLYPHVAULT_ROOM_ENGINE_H

#include "glyphvault/types.h"

int gv_render_current_room(gv_state *st, const char *atlas_path, int tile_size);
int gv_run_solver(gv_state *st, const char *atlas_path, int tile_size, const char *moves_path);

#endif
