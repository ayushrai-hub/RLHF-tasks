Audit and secure a Go middleware runner implementation. The project provides a CLI tool (`mwtool`) that reads a JSON configuration, validates a middleware specification, and optionally executes it in local or remote mode.

The current implementation contains security weaknesses that allow arbitrary command execution and access-control bypass. Locate them by reading the code and implement robust fixes that close every vector. The weaknesses are spread across the configuration, execution, and service layers, and several are independent: a change that closes one while leaving another open is an incomplete solution.

## Requirements

Fix the vulnerabilities by modifying source files under `src/` only. Do not modify files under `cmd/`. After fixing, rebuild the project binaries.

Every configuration in `testdata/valid/` must still be accepted (exit code 0). Every configuration in `testdata/exploits/` must be rejected with a non-zero exit and a diagnostic on stderr. Route each rejection through the security check that owns it, and make the diagnostic name that check so the reason is unambiguous. Use the vocabulary the owning check carries:

- an unapproved execution binary is refused by the binary allowlist (`binary` or `allowlist`);
- an unsafe local script is refused by the local script check (`local` or `script`);
- an unsafe or out-of-bounds remote path is refused by the remote path check (`remote` or `path`);
- a missing, disabled, or non-matching API credential is refused by the auth check (`api`, `token`, or `auth`).

Your fixes must be general rather than fixture-specific: do not hardcode values taken from the exploit files, and enforce each rule at the architectural boundary that owns it. Apply input validation consistently across both local and remote execution, so a safeguard present in one path is never missing from the other.

Two properties are easy to get subtly wrong, so treat them with care:

- API access must be granted only for a credential that exactly matches the configured admin token, and only while the middleware API is enabled. Do not widen the accepted set by normalizing the supplied credential before comparing it.
- Remote reads must stay confined to the `testdata/remote/` directory. Decide containment from the normalized path rather than the raw string, so a value that keeps an expected-looking prefix but resolves elsewhere is still refused.

Document your security improvements in `/app/environment/security_notes.md`. Cover each weakness you found and the defense you applied, organized by the source file that was changed. The notes must reference the actual filenames you edited: name at least three of `config.go`, `local_exec.go`, `remote_exec.go`, and `middleware_service.go`.
