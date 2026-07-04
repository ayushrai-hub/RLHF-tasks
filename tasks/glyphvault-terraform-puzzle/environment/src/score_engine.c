#include "glyphvault/score_engine.h"

#include <string.h>

#define ROOM_SCORE 10

/* BROKEN: awards room score only; ignores hint_weight and vault bonus hooks */
void gv_visit_room(gv_state *st, const char *room, const gv_clue_meta *meta, char glyph_ch) {
  (void)meta;
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
}

void gv_apply_vault_bonus(gv_state *st) {
    (void)st;
}
