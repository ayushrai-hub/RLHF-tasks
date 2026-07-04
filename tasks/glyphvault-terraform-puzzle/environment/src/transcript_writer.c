#include "glyphvault/transcript_writer.h"

#include <stdio.h>
#include <string.h>

/* BROKEN: emits glyphs_rendered before rooms_visited (wrong key order) */
int gv_write_transcript(const gv_transcript *t, const char *out_path) {
    if (!t || !out_path) return -1;
    FILE *fp = fopen(out_path, "w");
    if (!fp) return -1;
    fprintf(fp, "{\n");
    fprintf(fp, "  \"glyphs_rendered\": [\n");
    for (int i = 0; i < t->glyph_count; i++) {
        const gv_glyph_render *g = &t->glyphs[i];
        fprintf(fp,
                "    {\"room\": \"%s\", \"glyph_id\": \"%s\", \"char\": \"%c\", \"atlas_col\": %d, "
                "\"atlas_row\": %d}%s\n",
                g->room, g->glyph_id, g->ch, g->atlas_col, g->atlas_row,
                (i + 1 < t->glyph_count) ? "," : "");
    }
    fprintf(fp, "  ],\n");
    fprintf(fp, "  \"rooms_visited\": [");
    for (int i = 0; i < t->room_count; i++) {
        fprintf(fp, "%s\"%s\"", i ? ", " : "", t->rooms_visited[i]);
    }
    fprintf(fp, "],\n");
    fprintf(fp, "  \"moves_applied\": [");
    for (int i = 0; i < t->move_count; i++) {
        fprintf(fp, "%s\"%s\"", i ? ", " : "", t->moves_applied[i]);
    }
    fprintf(fp, "],\n");
    fprintf(fp, "  \"final_room\": \"%s\",\n", t->final_room);
    fprintf(fp, "  \"final_score\": %d,\n", t->final_score);
    fprintf(fp, "  \"has_key\": %s\n", t->has_key ? "true" : "false");
    fprintf(fp, "}\n");
    fclose(fp);
    return 0;
}

int gv_persist_score(sqlite3 *db, const gv_state *st) {
    if (!db || !st) return -1;
    char *err = NULL;
    char sql[512];
    snprintf(sql, sizeof(sql),
             "UPDATE puzzle_state SET current_room='%s', has_key=%d, final_score=%d WHERE id=1;",
             st->current_room, st->has_key, st->score);
    if (sqlite3_exec(db, sql, NULL, NULL, &err) != SQLITE_OK) {
        if (err) sqlite3_free(err);
        return -1;
    }
    return 0;
}
