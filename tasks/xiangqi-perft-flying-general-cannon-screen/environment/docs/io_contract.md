# Input and output contract

The program reads a single line from standard input with three whitespace
separated fields:

```
<placement> <side> <depth>
```

- `placement` is ten ranks from the top of the board to the bottom, separated by
  `/`. Within a rank the points run from the left file to the right file. A
  digit `1` to `9` is that many consecutive empty points. A letter is a piece:
  uppercase for the first player, lowercase for the second. The letters are
  `K` general, `A` advisor, `B` elephant, `N` horse, `R` chariot, `C` cannon,
  `P` soldier. This is the usual xiangqi FEN placement field.
- `side` is `w` if the first player is to move and `b` if the second player is
  to move. The first player is the side whose pieces are written in uppercase.
- `depth` is a non negative integer search depth.

The program prints one line to standard output: a single integer, the perft node
count. Perft of depth zero is one. Perft of depth `d` is the number of distinct
legal move sequences of exactly `d` plies starting from the position, which is
the sum over each legal move of the perft of depth `d - 1` of the resulting
position.

Read the position and generate moves under the complete standard rules of
xiangqi, with every piece movement, every capture, every check, and every
terminal and special case in scope. The output is compared for exact equality,
so the count must be neither high nor low.
