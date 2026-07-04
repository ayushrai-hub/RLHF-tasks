# Alias chain errata

`gv_resolve_room_alias` must loop: while the current id exists in `room_aliases.alias`, replace with `canonical` and repeat. Stop when no alias row matches. Clue fetch and exit lookup always use the fully resolved canonical room id.

Single-hop alias replacement is insufficient when future seeds add chained aliases.
