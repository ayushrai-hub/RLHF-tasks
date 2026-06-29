#ifndef LEGACY_ROOMS_H
#define LEGACY_ROOMS_H

/* Legacy hand-written room table (pre-migration). Retained for the --legacy
 * inspector and the interactive --play fallback. */
int legacy_room_count(void);
int legacy_room_id(int index);
const char *legacy_room_name(int index);

#endif /* LEGACY_ROOMS_H */
