# Cartridge schema

The cartridge is a single SQLite database, `cartridges/quests.cartridge.db`, shared by
every capsule. A capsule spec (`cartridges/<name>.qcap.json`) names this file in its
`cartridge` field and selects its rows by the capsule name. The database is read-only as
far as the loader is concerned; nothing here is regenerated at run time.

Columns whose names end in `_glyph` hold encoded payloads rather than readable text. The
encoding, the header format, and the run rules are not written down on the cartridge — they
are reconstructed in `docs/operator-log.md`. This file only states the table shapes.

## `glyphs`

| Column     | Type    | Meaning                                                       |
|------------|---------|---------------------------------------------------------------|
| `table_id` | integer | Glyph-set id. A capsule's header names which set to use.      |
| `code`     | text    | A symbol in the set.                                          |
| `plain`    | text    | The single character that symbol stands for.                  |

Primary key is (`table_id`, `code`). The cartridge currently ships one set.

## `rooms`

One row per room in a capsule.

| Column        | Type    | Meaning                                                    |
|---------------|---------|------------------------------------------------------------|
| `capsule`     | text    | Capsule name (matches the spec filename stem).             |
| `room_id`     | integer | Room id, unique within the capsule.                        |
| `kind`        | text    | `entry`, `exit`, or `normal`. Exactly one `entry` and one `exit` per capsule. |
| `title_glyph` | text    | Encoded room title.                                        |
| `body_glyph`  | text    | Encoded room description.                                  |

## `edges`

One row per directed exit out of a room.

| Column        | Type    | Meaning                                                    |
|---------------|---------|------------------------------------------------------------|
| `capsule`     | text    | Capsule name.                                              |
| `from_room`   | integer | Source room id.                                            |
| `label_glyph` | text    | Encoded choice label for this exit.                        |
| `to_room`     | integer | Destination room id (a plain integer, not encoded).        |
| `guard_glyph` | text    | Encoded guard token, or NULL for an unguarded exit.        |

## `seeds`

Save states. Each row is one challenge run to solve.

| Column       | Type    | Meaning                                          |
|--------------|---------|--------------------------------------------------|
| `capsule`    | text    | Capsule name.                                    |
| `seed_id`    | integer | Save-state id, unique within the capsule.        |
| `seed_value` | integer | The seed value that drives this run.             |
