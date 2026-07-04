#ifndef GLYPHVAULT_SCORE_ENGINE_H
#define GLYPHVAULT_SCORE_ENGINE_H

#include "glyphvault/types.h"

void gv_visit_room(gv_state *st, const char *room, const gv_clue_meta *meta, char glyph_ch);
void gv_apply_vault_bonus(gv_state *st);

#endif
