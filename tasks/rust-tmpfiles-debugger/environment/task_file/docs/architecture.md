# Architecture

The crate is intentionally small. `types.rs` contains the public API,
`parser.rs` converts config lines into internal rules, `glob.rs` handles the
documented glob subset, and `plan.rs` applies rules to the filesystem snapshot.

The verifier compiles extra integration tests against the public API, so private
helpers can change freely but exported names and fields must stay compatible.
