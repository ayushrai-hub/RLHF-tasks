# Activation-checkpointing planner

`ckptplan` is a Go command-line tool that chooses how to checkpoint a sequential
neural network. Given a budget `B`, it must find the segmentation of the layers
that minimizes recompute while keeping peak memory within `B`. It already parses
its input and prints a plan in the right shape, but the peak-memory value it
reports is not faithful and the segmentation it picks is not the cheapest one the
budget allows. Make both correct.

## Input and output

The subcommand is `ckptplan plan --budget B` (`B` a positive integer). Standard
input holds the network one layer per line in forward order; each line is two
non-negative integers, the layer's activation memory and its recompute cost
(blank lines ignored, at least one layer). A segmentation cuts the ordered layers
into contiguous segments; the first layer of each segment is a retained
checkpoint and the rest are recomputed from it, and the first layer is always a
segment start.

The tool prints one JSON object on a single line: the number of segments; the
zero-based segment-start indices in increasing order beginning with zero; the
peak memory; the recompute; the total activation memory over all layers; and
whether the plan is feasible. The number of segments equals the length of the
starts list. The parsing, field names, and output shape are already correct and
must not change.

## Objective

A segmentation's peak memory is the activation memory of its retained
checkpoints plus the largest single segment's total non-first-layer activation
memory; its recompute is the total recompute cost of all non-first layers. Report
the segmentation of minimum recompute among those whose peak memory is at most
`B`, breaking ties by fewer segments then lexicographically-earliest starts; if
none fits `B`, report the minimum-peak segmentation under the same tie-breaks,
marked not feasible.
