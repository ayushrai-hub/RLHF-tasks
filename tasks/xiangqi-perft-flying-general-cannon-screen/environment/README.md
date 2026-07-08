# Xiangqi perft engine

A small C++ project that counts perft nodes for a xiangqi position read from
standard input. The scaffold parses the position, drives the search, and prints
the result. The legal move generator behind it is not written yet.

- `src/` the engine sources. `src/movegen.cpp` holds the empty `legal_moves`
  and `apply_move` that need implementing; the rest of `src/` is the parser, the
  search driver, and the input and output.
- `data/` sample positions with known node counts for self checking.
- `docs/` the input and output contract, build and run notes, and the list of
  dependencies that are not allowed.
- `Makefile` builds `perft` from the sources under `src/`.
- `run_samples.sh` builds and checks the engine against the sample positions.

Build with `make` and run by piping a position and a depth into `./perft`. See
`docs/io_contract.md` for the exact input and output format.

The base image is the canonical GCC toolchain because the task is to build and
run this engine, so the compiler and `make` are needed at run time.
