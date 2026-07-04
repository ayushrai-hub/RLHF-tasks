#ifndef GLYPHVAULT_DIRECTION_MAP_H
#define GLYPHVAULT_DIRECTION_MAP_H

#include <sqlite3.h>

int gv_lookup_exit(sqlite3 *db, const char *from_room, const char *direction,
                   char *dest_out, int dest_len, int *requires_key_out);

#endif
