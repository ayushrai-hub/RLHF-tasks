#include "glyphvault/alias_resolver.h"

#include <sqlite3.h>
#include <string.h>

/* BROKEN: single lookup only; does not follow alias chain to canonical */
int gv_resolve_room_alias(sqlite3 *db, const char *room_or_alias, char *out, int out_len) {
    if (!db || !room_or_alias || !out || out_len <= 0) return -1;
    const char *sql = "SELECT canonical FROM room_aliases WHERE alias = ?1 LIMIT 1;";
    sqlite3_stmt *stmt = NULL;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(stmt, 1, room_or_alias, -1, SQLITE_STATIC);
    int rc = sqlite3_step(stmt);
    if (rc == SQLITE_ROW) {
        const char *canon = (const char *)sqlite3_column_text(stmt, 0);
        strncpy(out, canon, (size_t)out_len - 1);
        out[out_len - 1] = '\0';
        sqlite3_finalize(stmt);
        return 0;
    }
    sqlite3_finalize(stmt);
    strncpy(out, room_or_alias, (size_t)out_len - 1);
    out[out_len - 1] = '\0';
    return 0;
}
