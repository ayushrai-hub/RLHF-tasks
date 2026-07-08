Worked examples for the prefilter literal-set optimization.

These are sample input -> output pairs produced by the reference text-search engine.
Use them to work out the exact rule that Optimize must reproduce.

Files
  scenarios.txt   one input per line: "<id> <seq-json>"
  expected.txt    the reference output for each input, same order: "<id> <optimized-seq-json>"

A seq-json encodes a set of candidate literals in preference order:
  {"finite":true,"lits":[{"b":[104,105],"exact":true}, ...]}   a finite set
  {"finite":false}                                             "no literal set is worth scanning for"
where each literal's "b" is its bytes (0..255) and "exact" says whether the literal is
complete (true) or only a prefix fragment (false).

After building the project (cd /app && go build -o /app/litpre .) you can run the samples
through your implementation with

  /app/litpre /app/examples/scenarios.txt

and compare the result line-for-line against examples/expected.txt. These pairs cover
the range of behaviors the engine exhibits; the same rule is applied to other literal
sets of the same kind, so aim to match the reference in general, not only on these
lines.
