# Building and running

The sources live under `src`. Build from the project root with:

```
make
```

This compiles every `.cpp` under `src` into an executable named `perft` in the
project root. The grader builds the same way, by compiling the sources under
`src`, so keep the code there and keep it compiling.

Run the engine by piping one input line into it:

```
echo "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w 3" | ./perft
```

That prints the perft node count for the given position and depth.

The move generator in `src/movegen.cpp` is empty in the starter. Implementing
`legal_moves` and `apply_move` there is the work. The rest of the scaffold
(position parsing, the search driver, and input and output) is already written.

`run_samples.sh` builds the engine and checks it against the sample positions
under `data`.
