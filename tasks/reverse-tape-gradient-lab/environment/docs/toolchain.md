# Toolchain

Build from `/app/environment` with `/app/environment/scripts/rebuild.sh`. The script
compiles the Rust VM crate under `xk9` and installs four Go CLIs into
`/app/environment/build/`:

- `gradctl-run`
- `gradctl-probe`
- `gradctl-audit`
- `gradctl-inspect`

The container provides Go 1.24+ and Rust 1.85+ on `PATH`. Verifier tests call
`rebuild.sh` before each run. Digests use SHA-256 via `sha256sum`. Pytest runs from
`/opt/verifier-venv`.

Rust owns tape forward/backward kernels. Go owns graph compilation, broadcast shape
resolution, gradient-pool lifecycle, tape-epoch invalidation, export, and CLI surfaces.
