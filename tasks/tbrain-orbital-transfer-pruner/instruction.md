The tool in `/app` helps mission analysts compare small orbital transfer scenarios. Implement `/app/bin/transfer-pruner.js` so it reads the scenario JSON path passed on the command line and prints one JSON object to stdout.

The command should find the non-dominated transfer plans that reach the requested targets in the scenario. `/app/TRANSFER_RULES.md` is the binding public contract for the scenario fields, launch-window timing, resource token rules, target constraints, dominance behavior, output schema, and frontier ordering used by the analysis workflow.

The output object should contain a `frontier` array. Each frontier row should report `target`, `arrival`, `dv`, `dose`, and `path`; `path` is the visited body names for that plan.
