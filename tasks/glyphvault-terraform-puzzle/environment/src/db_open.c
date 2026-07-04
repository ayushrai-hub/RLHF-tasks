#include "glyphvault/db_open.h"

#include <stdio.h>
#include <sqlite3.h>

int gv_db_open(const char *path, sqlite3 **out) {
    if (!path || !out) return -1;
    return sqlite3_open(path, out);
}
