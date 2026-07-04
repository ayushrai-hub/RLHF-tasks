#!/usr/bin/env python3
"""Write corrected GlyphVault analyzer sources for oracle solution."""
from pathlib import Path

ENV = Path("/app/environment")

FILES = {
    "src/alias_resolver.c": r'''#include "glyphvault/alias_resolver.h"
#include "glyphvault/types.h"

#include <sqlite3.h>
#include <string.h>

int gv_resolve_room_alias(sqlite3 *db, const char *room_or_alias, char *out, int out_len) {
    if (!db || !room_or_alias || !out || out_len <= 0) return -1;
    char current[GV_MAX_ROOM];
    strncpy(current, room_or_alias, sizeof(current) - 1);
    current[sizeof(current) - 1] = '\0';

    const char *sql = "SELECT canonical FROM room_aliases WHERE alias = ?1 LIMIT 1;";
    for (;;) {
        sqlite3_stmt *stmt = NULL;
        if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) return -1;
        sqlite3_bind_text(stmt, 1, current, -1, SQLITE_STATIC);
        int rc = sqlite3_step(stmt);
        if (rc != SQLITE_ROW) {
            sqlite3_finalize(stmt);
            break;
        }
        const char *canon = (const char *)sqlite3_column_text(stmt, 0);
        strncpy(current, canon ? canon : current, sizeof(current) - 1);
        current[sizeof(current) - 1] = '\0';
        sqlite3_finalize(stmt);
    }
    strncpy(out, current, (size_t)out_len - 1);
    out[out_len - 1] = '\0';
    return 0;
}
''',
    "src/clue_query.c": r'''#include "glyphvault/clue_query.h"

#include <sqlite3.h>
#include <string.h>

int gv_fetch_clue_blob(sqlite3 *db, const char *canonical_room, char *out, int out_len) {
    if (!db || !canonical_room || !out || out_len <= 0) return -1;
    const char *sql = "SELECT clue_blob FROM room_clues WHERE room_id = ?1 LIMIT 1;";
    sqlite3_stmt *stmt = NULL;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(stmt, 1, canonical_room, -1, SQLITE_STATIC);
    if (sqlite3_step(stmt) != SQLITE_ROW) {
        sqlite3_finalize(stmt);
        return -1;
    }
    const char *blob = (const char *)sqlite3_column_text(stmt, 0);
    strncpy(out, blob ? blob : "", (size_t)out_len - 1);
    out[out_len - 1] = '\0';
    sqlite3_finalize(stmt);
    return 0;
}
''',
    "src/meta_decoder.c": r'''#include "glyphvault/meta_decoder.h"

#include <stdio.h>
#include <string.h>

static const char B64[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static int b64_index(char c) {
    const char *p = strchr(B64, c);
    return p ? (int)(p - B64) : -1;
}

static int b64_decode(const char *in, char *out, int out_len) {
    int len = 0;
    int val = 0, valb = -8;
    for (const char *p = in; *p; p++) {
        if (*p == '=') break;
        int idx = b64_index(*p);
        if (idx < 0) continue;
        val = (val << 6) + idx;
        valb += 6;
        if (valb >= 0) {
            if (len + 1 >= out_len) return -1;
            out[len++] = (char)((val >> valb) & 0xFF);
            valb -= 8;
        }
    }
    if (len >= out_len) return -1;
    out[len] = '\0';
    return len;
}

static int parse_json_fields(const char *json, gv_clue_meta *out) {
    int ac = 0, ar = 0, hw = 0;
    char gid[GV_MAX_ROOM] = {0};
    if (sscanf(json, "{\"atlas_col\":%d,\"atlas_row\":%d,\"glyph_id\":\"%31[^\"]\",\"hint_weight\":%d}",
               &ac, &ar, gid, &hw) < 4) {
        return -1;
    }
    out->atlas_col = ac;
    out->atlas_row = ar;
    strncpy(out->glyph_id, gid, sizeof(out->glyph_id) - 1);
    out->hint_weight = hw;
    return 0;
}

int gv_decode_clue_meta(const char *clue_blob, gv_clue_meta *out) {
    if (!clue_blob || !out) return -1;
    char json[512];
    if (b64_decode(clue_blob, json, sizeof(json)) < 0) return -1;
    return parse_json_fields(json, out);
}
''',
    "src/glyph_atlas.c": r'''#include "glyphvault/glyph_atlas.h"

#include <png.h>
#include <stdio.h>
#include <stdlib.h>

static png_bytep *rows = NULL;
static int img_w = 0;
static int img_h = 0;
static int tile_px = 8;

int gv_load_atlas(const char *png_path, int tile_size) {
    FILE *fp = fopen(png_path, "rb");
    if (!fp) return -1;
    png_structp png = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    png_infop info = png_create_info_struct(png);
    if (!png || !info) {
        fclose(fp);
        return -1;
    }
    if (setjmp(png_jmpbuf(png))) {
        png_destroy_read_struct(&png, &info, NULL);
        fclose(fp);
        return -1;
    }
    png_init_io(png, fp);
    png_read_info(png, info);
    img_w = (int)png_get_image_width(png, info);
    img_h = (int)png_get_image_height(png, info);
    tile_px = tile_size;
    rows = (png_bytep *)malloc(sizeof(png_bytep) * (size_t)img_h);
    for (int y = 0; y < img_h; y++) {
        rows[y] = (png_bytep)malloc(png_get_rowbytes(png, info));
    }
    png_read_image(png, rows);
    png_destroy_read_struct(&png, &info, NULL);
    fclose(fp);
    return 0;
}

char gv_sample_glyph(int atlas_col_1based, int atlas_row_1based) {
    if (!rows) return '?';
    int col = atlas_col_1based - 1;
    int row = atlas_row_1based - 1;
    int px = col * tile_px + tile_px / 2;
    int py = row * tile_px + tile_px / 2;
    if (px < 0 || py < 0 || px >= img_w || py >= img_h) return '?';
    png_bytep line = rows[py];
    return (char)line[px * 3];
}

void gv_unload_atlas(void) {
    if (!rows) return;
    for (int y = 0; y < img_h; y++) free(rows[y]);
    free(rows);
    rows = NULL;
}
''',
    "src/direction_map.c": r'''#include "glyphvault/direction_map.h"

#include <sqlite3.h>
#include <string.h>

int gv_lookup_exit(sqlite3 *db, const char *from_room, const char *direction,
                   char *dest_out, int dest_len, int *requires_key_out) {
    if (!db || !from_room || !direction || !dest_out || dest_len <= 0) return -1;
    if (requires_key_out) *requires_key_out = 0;
    const char *sql =
        "SELECT to_room, requires_key FROM room_exits WHERE from_room = ?1 AND direction = ?2 LIMIT 1;";
    sqlite3_stmt *stmt = NULL;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(stmt, 1, from_room, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, direction, -1, SQLITE_STATIC);
    if (sqlite3_step(stmt) != SQLITE_ROW) {
        sqlite3_finalize(stmt);
        dest_out[0] = '\0';
        return -1;
    }
    const char *dest = (const char *)sqlite3_column_text(stmt, 0);
    int rk = sqlite3_column_int(stmt, 1);
    strncpy(dest_out, dest ? dest : "", (size_t)dest_len - 1);
    dest_out[dest_len - 1] = '\0';
    if (requires_key_out) *requires_key_out = rk;
    sqlite3_finalize(stmt);
    return 0;
}
''',
    "src/unlock_gate.c": r'''#include "glyphvault/unlock_gate.h"

#include "glyphvault/types.h"

#include <string.h>

int gv_apply_unlock(gv_state *st, const char *direction) {
    if (!st || !direction) return -1;
    if (!st->has_key) return -1;
    if (strcmp(st->current_room, "crypt") == 0 && strcmp(direction, "east") == 0) {
        st->crypt_east_unlocked = 1;
        return 0;
    }
    return -1;
}
''',
    "src/score_engine.c": r'''#include "glyphvault/score_engine.h"

#include <string.h>

#define ROOM_SCORE 10
#define VAULT_BONUS 50

void gv_visit_room(gv_state *st, const char *room, const gv_clue_meta *meta, char glyph_ch) {
    (void)glyph_ch;
    if (!st || !room) return;
    int seen = 0;
    for (int i = 0; i < st->visited_count; i++) {
        if (strcmp(st->visited[i], room) == 0) {
            seen = 1;
            break;
        }
    }
    if (!seen && st->visited_count < GV_MAX_ROOM) {
        strncpy(st->visited[st->visited_count], room, GV_MAX_ROOM - 1);
        st->visited_count++;
        st->score += ROOM_SCORE;
    }
    if (meta) st->score += meta->hint_weight;
}

void gv_apply_vault_bonus(gv_state *st) {
    if (!st) return;
    if (strcmp(st->current_room, "vault") == 0) st->score += VAULT_BONUS;
}
''',
    "src/move_driver.c": r'''#include "glyphvault/move_driver.h"

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

int gv_load_moves(const char *path, char moves[][GV_MAX_LINE], int max_moves) {
    FILE *fp = fopen(path, "r");
    if (!fp) return -1;
    int count = 0;
    while (count < max_moves && fgets(moves[count], GV_MAX_LINE, fp)) {
        trim(moves[count]);
        if (moves[count][0] == '\0') continue;
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
        g->atlas_col = meta.atlas_col - 1;
        g->atlas_row = meta.atlas_row - 1;
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
''',
    "src/room_engine.c": r'''#include "glyphvault/room_engine.h"

#include "glyphvault/alias_resolver.h"
#include "glyphvault/clue_query.h"
#include "glyphvault/glyph_atlas.h"
#include "glyphvault/meta_decoder.h"
#include "glyphvault/move_driver.h"
#include "glyphvault/score_engine.h"

#include <string.h>

int gv_render_current_room(gv_state *st, const char *atlas_path, int tile_size) {
    if (!st || !atlas_path) return -1;
    if (gv_load_atlas(atlas_path, tile_size) != 0) return -1;
    char canon[GV_MAX_ROOM];
    gv_resolve_room_alias(st->db, st->current_room, canon, sizeof(canon));
    strncpy(st->current_room, canon, GV_MAX_ROOM - 1);
    char blob[512];
    gv_clue_meta meta;
    if (gv_fetch_clue_blob(st->db, canon, blob, sizeof(blob)) != 0) return -1;
    if (gv_decode_clue_meta(blob, &meta) != 0) return -1;
    char ch = gv_sample_glyph(meta.atlas_col, meta.atlas_row);
    gv_visit_room(st, canon, &meta, ch);
    if (st->glyph_count < GV_MAX_GLYPH) {
        gv_glyph_render *g = &st->glyphs[st->glyph_count++];
        strncpy(g->room, canon, GV_MAX_ROOM - 1);
        strncpy(g->glyph_id, meta.glyph_id, GV_MAX_ROOM - 1);
        g->ch = ch;
        g->atlas_col = meta.atlas_col - 1;
        g->atlas_row = meta.atlas_row - 1;
    }
    return 0;
}

int gv_run_solver(gv_state *st, const char *atlas_path, int tile_size, const char *moves_path) {
    if (!st || !atlas_path || !moves_path) return -1;
    if (gv_load_atlas(atlas_path, tile_size) != 0) return -1;
    if (gv_render_current_room(st, atlas_path, tile_size) != 0) return -1;

    char moves[GV_MAX_MOVE][GV_MAX_LINE];
    int n = gv_load_moves(moves_path, moves, GV_MAX_MOVE);
    if (n <= 0) return -1;
    for (int i = 0; i < n; i++) {
        if (gv_apply_move(st, moves[i]) != 0) return -1;
    }
    return 0;
}
''',
    "src/transcript_writer.c": r'''#include "glyphvault/transcript_writer.h"

#include <stdio.h>
#include <string.h>

int gv_write_transcript(const gv_transcript *t, const char *out_path) {
    if (!t || !out_path) return -1;
    FILE *fp = fopen(out_path, "w");
    if (!fp) return -1;
    fprintf(fp, "{\n");
    fprintf(fp, "  \"rooms_visited\": [");
    for (int i = 0; i < t->room_count; i++) {
        fprintf(fp, "%s\"%s\"", i ? ", " : "", t->rooms_visited[i]);
    }
    fprintf(fp, "],\n");
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
''',
    "src/tf_output_reader.c": r'''#define _POSIX_C_SOURCE 200809L

#include "glyphvault/tf_output_reader.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int gv_read_tile_size(const char *terraform_dir, int *tile_size_out) {
    if (!terraform_dir || !tile_size_out) return -1;
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "terraform -chdir=%s output -raw tile_size 2>/dev/null", terraform_dir);
    FILE *fp = popen(cmd, "r");
    if (!fp) return -1;
    char buf[64] = {0};
    if (!fgets(buf, sizeof(buf), fp)) {
        pclose(fp);
        return -1;
    }
    pclose(fp);
    *tile_size_out = atoi(buf);
    if (*tile_size_out <= 0) *tile_size_out = 8;
    return 0;
}
''',
}


def main() -> None:
    for rel, content in FILES.items():
        path = ENV / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"wrote {len(FILES)} fixed source files")


if __name__ == "__main__":
    main()
