# Sample positions

Each line in the `.txt` files here is one sanity case in four whitespace
separated fields:

```
<placement> <side> <depth> <expected_node_count>
```

The first three fields are exactly what the program reads on standard input (a
xiangqi placement, the side to move, and a search depth). The fourth field is
the perft node count a correct engine prints for that input.

`start_positions.txt` uses the standard opening position at shallow depths.
`sanity_positions.txt` and `quiet_positions.txt` use small hand made positions.
These cases only check that the engine builds and produces the right counts on
simple inputs; they are not a substitute for reasoning about the full ruleset,
because a perft count only reveals a subtle mistake a few plies deep.

`run_samples.sh` in the project root builds the engine and checks every line in
these files for you.
