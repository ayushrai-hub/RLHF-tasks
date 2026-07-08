# gatectl toolchain

Build the utility with:

```bash
CARGO_TARGET_DIR=/tmp/gatectl-build cargo build --manifest-path /app/environment/Cargo.toml
```

The verifier invokes `/tmp/gatectl-build/debug/gatectl`.

Rust and Cargo are on `PATH` inside the task image (`/usr/local/cargo/bin`).

Dispatch lane ordering is read from `/app/environment/runtime/dispatch.toml` at runtime.
