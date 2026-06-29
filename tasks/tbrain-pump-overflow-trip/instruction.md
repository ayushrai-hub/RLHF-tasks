The Go project in `/app` is an offline pump-station overflow protection engine. The final system must provide a working `overflow` command that reads one JSON scenario from standard input and writes one deterministic JSON ledger to standard output.

Use `/app/docs/spec.md` as the authoritative source for the input format, output format, and all required behavior. The ledger should report the result for every configured line in deterministic order. Invalid input should make the program exit nonzero without printing a ledger.

Keep the existing command-line interface intact. Only the engine behavior needs to change.
