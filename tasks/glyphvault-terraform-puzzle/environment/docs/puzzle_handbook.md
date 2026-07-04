# GlyphVault terminal puzzle handbook

The GlyphVault analysis engine under `/app/environment` replays a deterministic solver script against a Terraform-seeded SQLite clue database and renders room glyphs from `/app/environment/media/glyphs.png`. Operators report the puzzle exits after the first room, glyphs disagree with the atlas, and `/app/environment/artifacts/solve_transcript.json` never reaches the vault.

Normative behavior is spread across `/app/environment/docs/policy/`, `/app/environment/docs/errata/`, and `/app/environment/docs/reference/output_contract.md`. The verifier applies the Terraform fixture, compiles the C analyzer, runs `/app/environment/bin/puzzle-analyze`, and compares the transcript plus SQLite score state.

## Terraform fixture

`/app/environment/terraform` seeds `/app/environment/data/puzzle.sqlite` via `null_resource.seed_puzzle_db`. Outputs expose `tile_size` (not the deprecated `tile_px` key). Clue rows live in `room_clues.clue_blob` as base64-wrapped JSON metadata.

## Solver script

`/app/environment/scripts/solver.moves` lists one command per line. Supported verbs: `GO <direction>`, `TAKE key`, `UNLOCK <direction>`. Lines may end with CRLF; drivers must strip trailing `\r` before parsing.

## Scoring

- `10` points the first time a canonical room is entered
- add `hint_weight` from decoded clue metadata every time a room glyph is rendered
- `50` vault bonus when the final room is `vault`

## Room aliases

Terraform seeds alias rows (`foyer` → `entry`, `antechamber` → `hall`, `stacks` → `library`). Resolvers must follow alias chains until no further mapping exists before clue lookup or exit traversal.

## Locked exits

`room_exits.requires_key = 1` marks doors that need `UNLOCK <direction>` while holding the key taken in `library`. `UNLOCK` without the key must not open the passage.
