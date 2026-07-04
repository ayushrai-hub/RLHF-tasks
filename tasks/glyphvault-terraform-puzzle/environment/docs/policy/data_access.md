# Data access policy

Runtime puzzle facts (`room_exits`, `room_clues`, `room_aliases`, `puzzle_state`) must come from `/app/environment/data/puzzle.sqlite` after Terraform apply. Do not embed room graphs or clue blobs as C string constants. Regenerate `/app/environment/artifacts/solve_transcript.json` by running `/app/environment/bin/puzzle-analyze`.
