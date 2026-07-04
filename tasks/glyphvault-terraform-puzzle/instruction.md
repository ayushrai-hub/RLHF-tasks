# GlyphVault Terraform puzzle analyzer

The terminal puzzle at `/app/environment` exits after the first room because the C analysis engine misreads the Terraform-seeded clue database and renders wrong glyphs from `/app/environment/media/glyphs.png`. Operators need a repaired pipeline that queries SQLite for room state, decodes clue metadata into atlas coordinates, and drives `/app/environment/scripts/solver.moves` through the full dungeon to the vault.

Repair the C modules under `/app/environment/src/` and rebuild so `/app/environment/bin/puzzle-analyze` applies the Terraform fixture, compiles the analyzer, replays the solver script, and writes `/app/environment/artifacts/solve_transcript.json` plus updated `puzzle_state` rows per the contracts in:

- `/app/environment/docs/puzzle_handbook.md`
- `/app/environment/docs/policy/data_access.md`
- `/app/environment/docs/policy/exit_table.md`
- `/app/environment/docs/errata/clue_encoding.md`
- `/app/environment/docs/errata/atlas_coordinates.md`
- `/app/environment/docs/errata/alias_chain.md`
- `/app/environment/docs/reference/output_contract.md`

The verifier resets `/app/environment/data/puzzle.sqlite` from the seed copy, reapplies Terraform, deletes prior artifacts, and reruns `/app/environment/bin/puzzle-analyze`. Editing golden fixtures or verifier tests is not a substitute for fixing the engine.
