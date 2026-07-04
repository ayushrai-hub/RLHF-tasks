#include "glyphvault/direction_map.h"

#include <sqlite3.h>
#include <string.h>

/* BROKEN: hard-coded adjacency that omits garden/crypt/vault edges */
int gv_lookup_exit(sqlite3 *db, const char *from_room, const char *direction,
                   char *dest_out, int dest_len, int *requires_key_out) {
    (void)db;
    if (!from_room || !direction || !dest_out || dest_len <= 0) return -1;
    if (requires_key_out) *requires_key_out = 0;

    if (strcmp(from_room, "entry") == 0 && strcmp(direction, "east") == 0) {
        strncpy(dest_out, "hall", (size_t)dest_len - 1);
        return 0;
    }
    if (strcmp(from_room, "hall") == 0 && strcmp(direction, "north") == 0) {
        strncpy(dest_out, "library", (size_t)dest_len - 1);
        return 0;
    }
    if (strcmp(from_room, "library") == 0 && strcmp(direction, "south") == 0) {
        strncpy(dest_out, "hall", (size_t)dest_len - 1);
        return 0;
    }
    dest_out[0] = '\0';
    return -1;
}
