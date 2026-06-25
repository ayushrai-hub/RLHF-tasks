# Strace reconstruction contract

The strace lane parses fenced excerpt bodies line by line.

## openat paths

- Extract the quoted path from `openat(..., "PATH", ...)`.
- Compare against `run_dir` from `/app/policy/workflow_policy.toml` using prefix match after trimming trailing slashes on `run_dir`.
- Paths under `run_dir` are in-bounds; paths outside are candidates for `write_outside_run_dir` when surfaced by the policy evaluator.

## connect peers

- Parse `sin_port=htons(N)` and `sin_addr=inet_addr("IP")` on the same line.
- `sin_addr` and `sin_port` may appear in either order within the connect argument list.
- `htons` accepts decimal literals (`443`) or hexadecimal literals (`0x1BB`); decode hex before formatting `host:port`.
- Emit `host:port` with the numeric port from `htons`, not the symbolic service name.
- Loopback peers (`127.0.0.1`, `::1`, and any `127.*` address) are local health checks, not remote egress.

## IPv6 connect peers

- Parse `sin6_port=htons(N)` or `sin6_port=htons(0xNNN)` together with `sin6_addr=inet_pton(AF_INET6, "ADDR")` on the same line.
- Emit non-loopback IPv6 peers as `[ADDR]:port` in `socket_rows` and `network_egress` details.
- Treat `::1` and other IPv6 loopback addresses like IPv4 loopback: exclude them from remote egress lists.

## socket_rows in audit output

`policy_audit.json` `socket_rows` lists only non-loopback peers reconstructed from strace `connect` lines. Loopback connects must not appear in `socket_rows` even when present in a runbook excerpt.
