# Forbidden dependencies

The move generator and the search must be written from scratch. The grader
inspects the submitted sources and rejects the work if it pulls in an outside
game engine or a precomputed answer source.

Do not import, link, vendor, or shell out to any existing xiangqi or chess
engine or its bindings, including but not limited to Stockfish, Fairy Stockfish,
Pikafish, ElephantEye, XQWizard, and any `libxiangqi` or `cchess` style library.

Do not bundle a tablebase, an endgame database, an opening book, or any file of
precomputed node counts or move lists.

The build is offline and uses only the C++ standard library and the system
compiler. Nothing else is needed.
