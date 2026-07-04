#ifndef GLYPHVAULT_CLUE_QUERY_H
#define GLYPHVAULT_CLUE_QUERY_H

#include <sqlite3.h>

int gv_fetch_clue_blob(sqlite3 *db, const char *canonical_room, char *out, int out_len);

#endif
