#include "glyphvault/unlock_gate.h"

#include "glyphvault/types.h"

#include <string.h>

/* BROKEN: unlocks without requiring key in inventory */
int gv_apply_unlock(gv_state *st, const char *direction) {
    if (!st || !direction) return -1;
    if (strcmp(st->current_room, "crypt") == 0 && strcmp(direction, "east") == 0) {
        st->crypt_east_unlocked = 1;
        return 0;
    }
    return -1;
}
