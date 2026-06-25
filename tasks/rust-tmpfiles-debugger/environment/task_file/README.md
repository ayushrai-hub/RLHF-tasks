# tmpfiles_audit

`tmpfiles_audit` compiles a small, documented subset of tmpfiles-style host boot
cleanup rules into an action plan over an in-memory filesystem snapshot.

The public entry point is `TmpfilesConfig::compile_plan`. The contract is in
`docs/SPEC.md` and the supported config syntax is in `docs/format.md`.
