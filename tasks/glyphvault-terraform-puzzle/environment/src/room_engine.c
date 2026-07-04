#include "glyphvault/room_engine.h"

#include "glyphvault/glyph_atlas.h"
#include "glyphvault/move_driver.h"

#include <string.h>

int gv_render_current_room(gv_state *st, const char *atlas_path, int tile_size) {
    if (!st || !atlas_path) return -1;
    if (gv_load_atlas(atlas_path, tile_size) != 0) return -1;
    return gv_apply_move(st, "GO east") == 0 ? 0 : -1;
}

/* BROKEN: stops after first successful move (exits after room 1) */
int gv_run_solver(gv_state *st, const char *atlas_path, int tile_size, const char *moves_path) {
    if (!st || !atlas_path || !moves_path) return -1;
    if (gv_load_atlas(atlas_path, tile_size) != 0) return -1;

    char moves[GV_MAX_MOVE][GV_MAX_LINE];
    int n = gv_load_moves(moves_path, moves, GV_MAX_MOVE);
    if (n <= 0) return -1;

    if (gv_apply_move(st, moves[0]) != 0) return -1;
    return 0;
}
