#include "glyphvault/move_driver.h"

#include "glyphvault/alias_resolver.h"
#include "glyphvault/clue_query.h"
#include "glyphvault/direction_map.h"
#include "glyphvault/glyph_atlas.h"
#include "glyphvault/meta_decoder.h"
#include "glyphvault/score_engine.h"
#include "glyphvault/unlock_gate.h"

#include <ctype.h>
#include <stdio.h>
#include <string.h>

static void trim(char *s) {
    if (!s) return;
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == '\n' || s[n - 1] == '\r' || isspace((unsigned char)s[n - 1]))) {
        s[--n] = '\0';
    }
}

/* BROKEN: leaves CRLF on move lines */
int gv_load_moves(const char *path, char moves[][GV_MAX_LINE], int max_moves) {
    FILE *fp = fopen(path, "r");
    if (!fp) return -1;
    int count = 0;
    while (count < max_moves && fgets(moves[count], GV_MAX_LINE, fp)) {
        if (moves[count][0] == '\n' || moves[count][0] == '\0') continue;
        count++;
    }
    fclose(fp);
    return count;
}

static int render_room(gv_state *st, const char *room) {
    char blob[512];
    gv_clue_meta meta;
    if (gv_fetch_clue_blob(st->db, room, blob, sizeof(blob)) != 0) return -1;
    if (gv_decode_clue_meta(blob, &meta) != 0) return -1;
    char ch = gv_sample_glyph(meta.atlas_col, meta.atlas_row);
    gv_visit_room(st, room, &meta, ch);
    if (st->glyph_count < GV_MAX_GLYPH) {
        gv_glyph_render *g = &st->glyphs[st->glyph_count++];
        strncpy(g->room, room, GV_MAX_ROOM - 1);
        strncpy(g->glyph_id, meta.glyph_id, GV_MAX_ROOM - 1);
        g->ch = ch;
        g->atlas_col = meta.atlas_col;
        g->atlas_row = meta.atlas_row;
    }
    return 0;
}

int gv_apply_move(gv_state *st, const char *move_text) {
    if (!st || !move_text) return -1;
    char line[GV_MAX_LINE];
    strncpy(line, move_text, sizeof(line) - 1);
    line[sizeof(line) - 1] = '\0';
    trim(line);
    char verb[32] = {0};
    char arg[GV_MAX_ROOM] = {0};
    if (sscanf(line, "%31s %31s", verb, arg) < 1) return -1;

    if (strcmp(verb, "TAKE") == 0 && strcmp(arg, "key") == 0) {
        if (strcmp(st->current_room, "library") == 0) st->has_key = 1;
        return 0;
    }
    if (strcmp(verb, "UNLOCK") == 0) {
        return gv_apply_unlock(st, arg);
    }
    if (strcmp(verb, "GO") == 0) {
        char dest[GV_MAX_ROOM] = {0};
        int requires_key = 0;
        if (gv_lookup_exit(st->db, st->current_room, arg, dest, sizeof(dest), &requires_key) != 0) {
            return -1;
        }
        if (requires_key && !st->crypt_east_unlocked) return -1;
        char canon[GV_MAX_ROOM];
        gv_resolve_room_alias(st->db, dest, canon, sizeof(canon));
        strncpy(st->current_room, canon, GV_MAX_ROOM - 1);
        return render_room(st, canon);
    }
    return -1;
}
