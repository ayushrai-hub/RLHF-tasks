#ifndef GLYPHVAULT_DB_OPEN_H
#define GLYPHVAULT_DB_OPEN_H

#include <sqlite3.h>

int gv_db_open(const char *path, sqlite3 **out);

#endif
