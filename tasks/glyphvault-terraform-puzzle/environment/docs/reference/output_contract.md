# Output contract

`/app/environment/artifacts/solve_transcript.json` keys in order:

1. `rooms_visited` — JSON array of canonical room ids in visit order (first entry only once for scoring, but re-entries still render glyphs)
2. `glyphs_rendered` — array of objects `{room, glyph_id, char, atlas_col, atlas_row}` where `atlas_col`/`atlas_row` are **0-based** tile indices
3. `moves_applied` — array of move strings exactly as read from the solver script after CRLF trim
4. `final_room` — canonical room id after the last move
5. `final_score` — integer including vault bonus when applicable
6. `has_key` — boolean

`puzzle_state.final_score` in SQLite must match `final_score` in the transcript after a successful analyze run.
