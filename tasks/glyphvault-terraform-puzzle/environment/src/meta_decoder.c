#include "glyphvault/meta_decoder.h"

#include <stdio.h>
#include <string.h>

/* BROKEN: parses clue_blob as raw JSON without base64 decode per clue_encoding errata */
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
    return parse_json_fields(clue_blob, out);
}
