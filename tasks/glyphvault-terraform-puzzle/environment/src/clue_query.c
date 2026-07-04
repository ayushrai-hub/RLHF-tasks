#include "glyphvault/clue_query.h"

#include <sqlite3.h>
#include <string.h>

/* BROKEN: queries legacy clues table and clue_text column */
int gv_fetch_clue_blob(sqlite3 *db, const char *canonical_room, char *out, int out_len) {
    if (!db || !canonical_room || !out || out_len <= 0) return -1;
    const char *sql = "SELECT clue_text FROM clues WHERE room = ?1 LIMIT 1;";
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
