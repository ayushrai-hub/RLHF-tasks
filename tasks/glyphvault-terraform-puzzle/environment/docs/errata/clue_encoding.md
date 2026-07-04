# Clue encoding errata

`room_clues.clue_blob` stores **base64-encoded UTF-8 JSON**, not raw JSON text. Decode base64 before parsing fields:

- `atlas_col` and `atlas_row` are **1-based** tile coordinates in the PNG atlas (see `atlas_coordinates.md`).
- `glyph_id` matches the canonical room id.
- `hint_weight` is an integer added to score on each render.

Legacy `clues.clue_text` rows are obsolete and must not be queried.
