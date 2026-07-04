#ifndef GLYPHVAULT_ALIAS_RESOLVER_H
#define GLYPHVAULT_ALIAS_RESOLVER_H

#include <sqlite3.h>

int gv_resolve_room_alias(sqlite3 *db, const char *room_or_alias, char *out, int out_len);

#endif
