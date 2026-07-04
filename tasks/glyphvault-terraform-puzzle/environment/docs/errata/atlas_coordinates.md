# Atlas coordinates errata

`/app/environment/media/glyphs.png` is a 4×3 grid of `tile_size`×`tile_size` RGB tiles (default `tile_size = 8` from Terraform output `tile_size`).

When sampling a glyph character:

1. Read `tile_size` via `terraform output -raw tile_size`.
2. Convert clue `atlas_col` / `atlas_row` from **1-based** metadata to **0-based** indices by subtracting one.
3. Sample the center pixel of tile `(col, row)` where **col is X** and **row is Y**. Do not swap axes.

The rendered character is the red channel byte at the tile center.
