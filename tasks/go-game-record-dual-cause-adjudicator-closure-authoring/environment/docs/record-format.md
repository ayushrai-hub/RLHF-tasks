# Local game-record format

A `.ggr` file is a line-oriented tournament record. Header keys use `key: value`; the required keys are `record_id`, `ruleset`, `board_size`, and `komi`. The `main:` section contains numbered moves as `N B A1`, `N W C3`, or `N B pass`. A branch is written as `variation NAME from N:` and must finish with `endvariation`; branch moves replay from the snapshot after main move `N` and must not change the final main-line board.

The score line is either an area sheet, `score black_area=NN white_area=NN`, or a legacy token, `score B+M.M` or `score W+M.M`. New area scores use the rulebook komi to resolve `result`. Legacy score tokens are accepted only when the rulebook and the independent adjudicator policy both allow them.
