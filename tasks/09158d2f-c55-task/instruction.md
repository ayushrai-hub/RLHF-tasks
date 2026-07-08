I need a build planner for a version-control tool that figures out which objects
and targets are stale and need rebuilding, and what order to rebuild them in.

Build rules live in `/app/cases/<name>.mk`, one rule per line as
`target: dep1 dep2 ...` (blank lines and `#` comments are skipped). The current
tree state is in `/app/cases/<name>.state`, one `name mtime` pair per line -- if a
name doesn't appear it doesn't exist yet. Names that never appear on the left-hand
side of a rule are source files.

For each scenario write the list of targets to rebuild, in build order, to
`/app/out/<name>.txt` (one target per line, empty file if nothing needs
rebuilding). Create `/app/out` if it doesn't exist.

Look at `/app/examples` -- there are pairs of input files and their correct output
under `/app/examples/expected`. Your planner must reproduce those exactly, then run
on every scenario in `/app/cases`.
