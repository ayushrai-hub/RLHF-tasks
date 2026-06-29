I want a continued-fraction calculator in C++ at `/app/contfrac.cpp`, built with `g++ -O2 -std=c++17 -o /app/contfrac /app/contfrac.cpp`. It reads one command per line from stdin and writes one line per command to stdout. The (simple) continued fraction of a rational `p/q` is the integer sequence `[a0; a1, a2, ...]` produced by the Euclidean algorithm: repeatedly take the floor and invert the remainder. The first term may be negative; the rest are positive.

- `CF <p> <q>` — print the continued-fraction terms of `p/q` (with `q > 0`), space-separated.
- `LEN <p> <q>` — print the number of terms.
- `VALUE <a0> [a1 ...]` — evaluate the continued fraction `[a0; a1, ...]` back to a single rational, printed in lowest terms as `p` or `p/q`.

Errors: `q <= 0` prints `ERROR: range`; a non-integer argument prints `ERROR: parse`; a `VALUE` that divides by zero prints `ERROR: divzero`; a wrong argument count prints `ERROR: usage`; an unrecognized command prints `ERROR: unknown command`.
