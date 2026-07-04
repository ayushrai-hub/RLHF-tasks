#ifndef GLYPHVAULT_TYPES_H
#define GLYPHVAULT_TYPES_H

#include <sqlite3.h>

#define GV_MAX_ROOM 32
#define GV_MAX_MOVE 128
#define GV_MAX_GLYPH 32
#define GV_MAX_LINE 256

typedef struct {
    int atlas_col;
    int atlas_row;
    char glyph_id[GV_MAX_ROOM];
    int hint_weight;
} gv_clue_meta;

typedef struct {
    char room[GV_MAX_ROOM];
    char glyph_id[GV_MAX_ROOM];
    char ch;
    int atlas_col;
    int atlas_row;
} gv_glyph_render;

typedef struct {
    char rooms_visited[GV_MAX_ROOM][GV_MAX_ROOM];
    int room_count;
    gv_glyph_render glyphs[GV_MAX_GLYPH];
    int glyph_count;
    char moves_applied[GV_MAX_MOVE][GV_MAX_LINE];
    int move_count;
    char final_room[GV_MAX_ROOM];
    int final_score;
    int has_key;
} gv_transcript;

typedef struct {
    sqlite3 *db;
    char current_room[GV_MAX_ROOM];
    int has_key;
    int crypt_east_unlocked;
    int score;
    char visited[GV_MAX_ROOM][GV_MAX_ROOM];
    int visited_count;
    gv_glyph_render glyphs[GV_MAX_GLYPH];
    int glyph_count;
} gv_state;

#endif
