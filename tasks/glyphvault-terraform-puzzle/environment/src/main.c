#include "glyphvault/db_open.h"
#include "glyphvault/glyph_atlas.h"
#include "glyphvault/room_engine.h"
#include "glyphvault/score_engine.h"
#include "glyphvault/tf_output_reader.h"
#include "glyphvault/transcript_writer.h"
#include "glyphvault/types.h"

#include <stdio.h>
#include <string.h>

static void state_to_transcript(const gv_state *st, gv_transcript *t, char moves[][GV_MAX_LINE], int move_count) {
    memset(t, 0, sizeof(*t));
    t->room_count = st->visited_count;
    for (int i = 0; i < st->visited_count; i++) {
        strncpy(t->rooms_visited[i], st->visited[i], GV_MAX_ROOM - 1);
    }
    t->glyph_count = st->glyph_count;
    for (int i = 0; i < st->glyph_count; i++) {
        t->glyphs[i] = st->glyphs[i];
    }
    t->move_count = move_count;
    for (int i = 0; i < move_count; i++) {
        strncpy(t->moves_applied[i], moves[i], GV_MAX_LINE - 1);
    }
    strncpy(t->final_room, st->current_room, GV_MAX_ROOM - 1);
    t->final_score = st->score;
    t->has_key = st->has_key;
}

int main(int argc, char **argv) {
    const char *db_path = "/app/environment/data/puzzle.sqlite";
    const char *atlas_path = "/app/environment/media/glyphs.png";
    const char *moves_path = "/app/environment/scripts/solver.moves";
    const char *out_path = "/app/environment/artifacts/solve_transcript.json";
    const char *tf_dir = "/app/environment/terraform";

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--db") == 0 && i + 1 < argc) db_path = argv[++i];
        else if (strcmp(argv[i], "--atlas") == 0 && i + 1 < argc) atlas_path = argv[++i];
        else if (strcmp(argv[i], "--moves") == 0 && i + 1 < argc) moves_path = argv[++i];
        else if (strcmp(argv[i], "--out") == 0 && i + 1 < argc) out_path = argv[++i];
        else if (strcmp(argv[i], "--terraform") == 0 && i + 1 < argc) tf_dir = argv[++i];
    }

    sqlite3 *db = NULL;
    if (gv_db_open(db_path, &db) != 0 || !db) {
        fprintf(stderr, "db open failed\n");
        return 1;
    }

    int tile_size = 8;
    gv_read_tile_size(tf_dir, &tile_size);

    gv_state st;
    memset(&st, 0, sizeof(st));
    st.db = db;
    strncpy(st.current_room, "entry", GV_MAX_ROOM - 1);

    if (gv_run_solver(&st, atlas_path, tile_size, moves_path) != 0) {
        sqlite3_close(db);
        return 1;
    }

    if (strcmp(st.current_room, "vault") == 0) {
        gv_apply_vault_bonus(&st);
    }

    char moves[GV_MAX_MOVE][GV_MAX_LINE];
    int move_count = 0;
    FILE *mf = fopen(moves_path, "r");
    if (mf) {
        while (move_count < GV_MAX_MOVE && fgets(moves[move_count], GV_MAX_LINE, mf)) {
            if (moves[move_count][0] == '\n') continue;
            size_t n = strlen(moves[move_count]);
            while (n > 0 && (moves[move_count][n - 1] == '\n' || moves[move_count][n - 1] == '\r')) {
                moves[move_count][--n] = '\0';
            }
            move_count++;
        }
        fclose(mf);
    }

    gv_transcript tr;
    state_to_transcript(&st, &tr, moves, move_count);
    if (gv_write_transcript(&tr, out_path) != 0) {
        sqlite3_close(db);
        return 1;
    }
    if (gv_persist_score(db, &st) != 0) {
        sqlite3_close(db);
        return 1;
    }

    gv_unload_atlas();
    sqlite3_close(db);
    return 0;
}
