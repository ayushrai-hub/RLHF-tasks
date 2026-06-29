# Game replay chronicle normalizer

Build the canonical chronicle pipeline for competitive game replay shards. Raw .grsh shard files may arrive out of order, carry duplicate frames, include per-shard tick drift, or fail integrity checks. Implement the Go CLI at /app/bin/replay-chronicle to normalize a directory of shards into a single chronicle JSON document, and implement the Bash utilities /app/scripts/replay-pack.sh and /app/scripts/replay-unpack.sh to round-trip that chronicle through the packed .grpl transport format.

Behavior is fully specified in /app/docs/replay-format.md, /app/docs/chronicle-schema.md, /app/docs/drift-policy.md, and /app/docs/pack-contract.md. The CLI subcommands are normalize (directory of shards → chronicle JSON) and validate (verify an existing chronicle’s integrity field). When the environment variable TB3_FIXTURE_ROOT is set, both commands must read inputs from that directory instead of the --input / --input-dir path (used for verifier-only fixture roots under /opt/verifier-fixtures/).

Rebuild with make or /opt/verifier-scripts/rebuild-game-replay-chronicle-normalizer before running the tools.
