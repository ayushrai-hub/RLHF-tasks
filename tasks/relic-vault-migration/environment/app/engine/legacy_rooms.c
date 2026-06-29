/* Legacy hand-written room table. This is the small, pre-migration loader the
 * engine used before the season-archive arrived; the migrated vault.pack
 * supersedes it for replay and play modes. */

#include "legacy_rooms.h"

typedef struct {
    int id;
    const char *name;
} LegacyRoom;

static const LegacyRoom LEGACY_ROOMS[] = {
    {1, "Old Cistern"},
    {2, "Collapsed Stair"},
    {3, "Tallow Vestibule"},
    {4, "Forgotten Oratory"},
};

int legacy_room_count(void) {
    return (int)(sizeof(LEGACY_ROOMS) / sizeof(LEGACY_ROOMS[0]));
}

int legacy_room_id(int index) {
    if (index < 0 || index >= legacy_room_count()) return -1;
    return LEGACY_ROOMS[index].id;
}

const char *legacy_room_name(int index) {
    if (index < 0 || index >= legacy_room_count()) return "?";
    return LEGACY_ROOMS[index].name;
}
