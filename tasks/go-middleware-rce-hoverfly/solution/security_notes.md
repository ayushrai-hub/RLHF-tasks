# Security Notes - Go Middleware Runner

## config.go - Binary Allowlist
Added a binary allowlist in the config validation layer that restricts execution to known-safe binaries (mw-runner). Any binary not on the allowlist is rejected at configuration parse time, preventing arbitrary binary execution through the middleware configuration.

## local_exec.go - Shell Injection Prevention
Removed the shell-based execution path (`sh -c`) and replaced it with direct `exec.Command` invocation. Added a script safety check that rejects shell metacharacters before execution. This prevents an attacker from injecting arbitrary commands through the middleware script field.

## remote_exec.go - Remote Path Validation
Replaced shell-based remote execution with direct file access using `os.Open`. A prefix check alone is insufficient: a value such as `testdata/remote/../../etc/passwd` shares the allowed prefix yet escapes the directory. The path is therefore canonicalized with `filepath.Clean` and the result is verified (via `filepath.Rel`) to remain confined within the `testdata/remote/` root. Absolute paths and any path that resolves outside the root are rejected. The same script-safety check used by the local executor is applied here as well, so the script field cannot inject commands in remote mode either. This neutralizes both command injection and directory-traversal reads through the remote path field.

## middleware_service.go - API Access Gating
Added an authentication check at the entry of `SetMiddleware` that validates the auth token before any middleware processing occurs. When the API is enabled, requests must provide a valid admin token or they are rejected with an access denied diagnostic.

## auth.go - Exact Token Comparison
The original token check normalized the supplied token (case-folding and trimming whitespace) before comparing it to the admin token, so near-miss values such as `ADMIN-TOKEN` or a whitespace-padded copy authenticated. Wiring the guard into `SetMiddleware` alone does not close this gap. The comparison is now an exact, constant-time match via `crypto/subtle.ConstantTimeCompare`, so only the byte-for-byte admin token is accepted and timing does not leak how many leading characters matched.
